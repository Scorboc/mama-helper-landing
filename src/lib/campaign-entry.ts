/** Only campaign labels may follow the visitor. Never propagate invite tokens or free text. */
export function campaignAccountPath(search: string): string {
  const source = new URLSearchParams(search);
  const target = new URLSearchParams({ mode: "login" });
  for (const key of ["utm_source", "utm_medium", "utm_campaign", "utm_content"]) {
    const values = source.getAll(key);
    if (values.length === 1 && /^[a-z0-9_-]{1,64}$/.test(values[0])) target.set(key, values[0]);
  }
  return `/account?${target}`;
}
