/** Keep the same application deployable at a domain root or GitHub Pages path. */
export function asset(path: string): string {
  if (path.startsWith("/api/") || /^(https?:|blob:|data:)/.test(path))
    return path;
  return import.meta.env.BASE_URL + path.replace(/^\//, "");
}
