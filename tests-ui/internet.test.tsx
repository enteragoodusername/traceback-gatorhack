import { describe, it, expect } from "vitest";
import { embedUrl, watchUrl } from "../src/internet";
describe("external video links", () => {
  it("constructs trusted embeds instead of rendering search-provider HTML", () => {
    expect(embedUrl("https://www.youtube.com/watch?v=abcdefghijk")).toBe(
      "https://www.youtube-nocookie.com/embed/abcdefghijk",
    );
    expect(embedUrl("https://archive.org/details/space-film")).toBe(
      "https://archive.org/embed/space-film",
    );
  });
  it("rejects executable and unsupported destinations", () => {
    for (const url of [
      "javascript:alert(1)",
      "https://evil.example/watch?v=abcdefghijk",
      "https://www.youtube.com.evil.example/watch?v=abcdefghijk",
      "http://www.youtube.com/watch?v=abcdefghijk",
      "https://archive.org/details/../../admin",
    ])
      expect(watchUrl(url)).toBeUndefined();
  });
});
