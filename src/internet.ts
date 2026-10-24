export type VideoCandidate = {
  id: string;
  title: string;
  url: string;
  provider: string;
  creator: string;
  duration: string;
  published: string;
  thumbnail?: string;
  similarity?: number;
  matchedFrame?: number;
};
export type VideoSearch = {
  schemaVersion: string;
  searchedAt: string;
  query: { filename: string; duration: number; sha256: string };
  queries: string[];
  captions: string[];
  frames: { time: number; image: string }[];
  results: VideoCandidate[];
  providers: {
    provider: string;
    query: string;
    status: string;
    count: number;
  }[];
  warnings: string[];
  elapsedSeconds: number;
  limitation: string;
};
export type SavedVideo = VideoCandidate & { imageUrl?: string };
export function watchUrl(url: string): string | undefined {
  try {
    const u = new URL(url);
    if (
      u.protocol !== "https:" ||
      u.username ||
      u.password ||
      (u.port && u.port !== "443")
    )
      return;
    if (
      u.hostname === "www.youtube.com" &&
      u.pathname === "/watch" &&
      /^[\w-]{11}$/.test(u.searchParams.get("v") || "")
    )
      return u.href;
    if (u.hostname === "archive.org" && /^\/details\/[\w.-]+$/.test(u.pathname))
      return u.href;
  } catch {
    /* Invalid third-party metadata is not a navigable URL. */
  }
}
export function embedUrl(url: string): string | undefined {
  const safe = watchUrl(url);
  if (!safe) return;
  const u = new URL(safe);
  if (u.hostname === "www.youtube.com")
    return `https://www.youtube-nocookie.com/embed/${u.searchParams.get("v")}`;
  return `https://archive.org/embed/${u.pathname.split("/").pop()}`;
}
export const timestamp = (n: number) =>
  `${Math.floor(n / 60)
    .toString()
    .padStart(2, "0")}:${(n % 60).toFixed(1).padStart(4, "0")}`;
