export const CARE_READ_LIMIT_MESSAGE = 'Слишком много обновлений, попробуйте через минуту';

// Memory only: no family records are persisted in browser storage.
export class CareReads {
  private entries = new Map<string, { promise: Promise<unknown>; until: number }>();
  private generation = 0;
  private session = 0;
  private blockedUntil = 0;
  constructor(private now = () => Date.now()) {}

  invalidate() { this.generation++; this.entries.clear(); }
  reset() { this.session++; this.invalidate(); this.blockedUntil = 0; }

  read<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
    if (this.now() < this.blockedUntil)
      return Promise.reject(Object.assign(new Error(CARE_READ_LIMIT_MESSAGE), { status: 429 }));
    const existing = this.entries.get(key);
    if (existing && existing.until > this.now()) return existing.promise as Promise<T>;
    const generation = this.generation;
    const session = this.session;
    const entry = { promise: undefined as unknown as Promise<T>, until: Infinity };
    entry.promise = Promise.resolve().then(fetcher).then(value => {
      if (session !== this.session)
        throw Object.assign(new Error('Доступ изменился. Обновите страницу.'), { status: 409 });
      // A write during a read must not deliver or cache the pre-write snapshot.
      if (generation !== this.generation) return this.read(key, fetcher);
      entry.until = this.now() + 2500;
      return value;
    }).catch(error => {
      if (this.entries.get(key) === entry) this.entries.delete(key);
      if (session === this.session && error?.status === 429) {
        this.blockedUntil = this.now() + 60000;
        error.message = CARE_READ_LIMIT_MESSAGE;
      }
      throw error;
    });
    this.entries.set(key, entry);
    return entry.promise;
  }
}
