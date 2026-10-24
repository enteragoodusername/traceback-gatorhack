import type { VideoSearch } from "../src/internet";
export const jobId = "c".repeat(32);
// Test-only API contract. Production never imports this file.
export const search: VideoSearch = {
  schemaVersion: "internet-1",
  searchedAt: "2026-10-24T12:00:00Z",
  query: { filename: "my-clip.mp4", duration: 8, sha256: "a".repeat(64) },
  queries: ["a rocket launching into the sky"],
  captions: ["a rocket launching into the sky"],
  frames: [
    { time: 1.2, image: "query-0.jpg" },
    { time: 4, image: "query-1.jpg" },
  ],
  results: [
    {
      id: "youtube-abcdefghijk",
      title: "Rocket launch from the coast",
      url: "https://www.youtube.com/watch?v=abcdefghijk",
      provider: "YouTube",
      creator: "Space channel",
      duration: "3:20",
      published: "1 year ago",
      thumbnail: "youtube-abcdefghijk.jpg",
      similarity: 0.74,
      matchedFrame: 1,
    },
    {
      id: "archive-space-film",
      title: "Historic space flight",
      url: "https://archive.org/details/space-film",
      provider: "Internet Archive",
      creator: "Archive contributor",
      duration: "",
      published: "",
      thumbnail: "archive-space-film.jpg",
      similarity: 0.56,
      matchedFrame: 0,
    },
  ],
  providers: [
    {
      provider: "YouTube",
      query: "a rocket launching into the sky",
      status: "ok",
      count: 1,
    },
  ],
  warnings: [],
  elapsedSeconds: 12,
  limitation: "Thumbnail similarity does not verify a source.",
};
