/** Reject late responses after a newer request or a child/day change. */
export class RequestScope {
  private context = '';
  private generation = 0;
  select(context: string) {
    if (context !== this.context) { this.context = context; this.generation++; }
  }
  begin(context: string) { this.select(context); return ++this.generation; }
  current(ticket: number) { return ticket === this.generation; }
  cancel() { this.generation++; }
}
