import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Library from "../src/Library";
import manifest from "../public/manifest.json";
import saved from "../public/semantic-searches.json";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/semantic-searches.json")
        return { ok: true, json: async () => saved };
      if (url === "/api/search")
        return {
          ok: true,
          json: async () => ({
            results: [{ sourceId: "bridge", time: 8, similarity: 0.73 }],
          }),
        };
      throw Error(`Unexpected request ${url}`);
    }),
  );
});

describe("semantic library search", () => {
  it("uses recorded retrieval honestly and opens the retrieved timestamp", async () => {
    const user = userEvent.setup();
    const inspect = vi.fn();
    render(
      <Library
        manifest={manifest}
        health={null}
        onInspect={inspect}
        onSources={() => {}}
      />,
    );
    await user.click(
      await screen.findByRole("button", { name: saved.searches[0].query }),
    );
    expect(
      screen.getByText("Recorded text-to-frame retrieval"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Similarity is not proof of reuse"),
    ).toBeInTheDocument();
    const hit = saved.searches[0].results[0];
    const source = manifest.sources.find((s) => s.id === hit.sourceId)!;
    const image = screen.getAllByAltText(new RegExp(source.title + " at"))[0];
    await user.click(image.closest("button")!);
    expect(inspect).toHaveBeenCalledWith(source, hit.time);
  });
  it("does not fabricate arbitrary hosted search results", async () => {
    const user = userEvent.setup();
    render(
      <Library
        manifest={manifest}
        health={null}
        onInspect={() => {}}
        onSources={() => {}}
      />,
    );
    await user.type(
      screen.getByRole("textbox", { name: "Describe a visual moment" }),
      "A purple elephant",
    );
    await user.click(
      screen.getByRole("button", { name: "Search", exact: true }),
    );
    expect(
      await screen.findByText(
        /Free-text semantic search runs on the local engine/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Live text-to-frame retrieval"),
    ).not.toBeInTheDocument();
  });
  it("requests live search and shows the actual indexed moment", async () => {
    const user = userEvent.setup();
    render(
      <Library
        manifest={manifest}
        health={{ semantic: true }}
        onInspect={() => {}}
        onSources={() => {}}
      />,
    );
    await user.type(
      screen.getByRole("textbox", { name: "Describe a visual moment" }),
      "People by a canal",
    );
    await user.click(
      screen.getByRole("button", { name: "Search", exact: true }),
    );
    expect(
      await screen.findByText("Live text-to-frame retrieval"),
    ).toBeInTheDocument();
    expect(screen.getByAltText("The bridge at 00:08")).toHaveAttribute(
      "src",
      "/api/frames/bridge/8",
    );
    expect(fetch).toHaveBeenCalledWith(
      "/api/search",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ query: "People by a canal" }),
      }),
    );
  });
});
