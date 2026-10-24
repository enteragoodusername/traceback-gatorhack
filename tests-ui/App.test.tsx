import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, it, expect, vi } from "vitest";
import App from "../src/App";
import { search, jobId } from "./internet-fixture";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/api/health")
        return { ok: true, json: async () => ({ mode: "internet-search" }) };
      if (url === "/api/search-video" || url.startsWith("/api/refine/"))
        return { ok: true, json: async () => ({ id: jobId }) };
      if (url === `/api/jobs/${jobId}`)
        return {
          ok: true,
          json: async () => ({ status: "complete", result: search }),
        };
      throw Error(`Unexpected fetch: ${url}`);
    }),
  );
  URL.createObjectURL = vi.fn(() => "blob:clip-preview");
  URL.revokeObjectURL = vi.fn();
});
async function upload() {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("Live engine connected");
  await user.upload(
    screen.getByLabelText("Choose a video file"),
    new File(["video"], "my-clip.mp4", { type: "video/mp4" }),
  );
  await screen.findByText("Similar videos to explore");
  return user;
}

describe("single-input live internet search", () => {
  it("starts immediately on file selection, sends only the file, and never requests a fixture", async () => {
    await upload();
    const call = vi
      .mocked(fetch)
      .mock.calls.find(([url]) => url === "/api/search-video")!;
    const form = call[1]?.body as FormData;
    expect([...form.keys()]).toEqual(["file"]);
    expect((form.get("file") as File).name).toBe("my-clip.mp4");
    expect(
      screen.queryByRole("button", { name: "Submit" }),
    ).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringMatching(/manifest|evidence|semantic-searches|report\.json/),
    );
    expect(
      screen.getByRole("link", { name: "Rocket launch from the coast" }),
    ).toHaveAttribute("href", search.results[0].url);
    expect(
      screen.getByText(/Searched for.*a rocket launching into the sky/),
    ).toBeInTheDocument();
  });
  it("supports dropping one video and rejects invalid files before sending anything", async () => {
    render(<App />);
    await screen.findByText("Live engine connected");
    const drop = screen.getByRole("region", { name: "Submit a video" });
    fireEvent.drop(drop, {
      dataTransfer: { files: [new File(["text"], "notes.txt")] },
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Choose an MP4");
    expect(
      vi.mocked(fetch).mock.calls.some(([url]) => url === "/api/search-video"),
    ).toBe(false);
    fireEvent.drop(drop, {
      dataTransfer: {
        files: [new File(["video"], "dropped.mp4", { type: "video/mp4" })],
      },
    });
    await screen.findByText("Similar videos to explore");
    expect(
      screen.getByRole("heading", { name: "dropped.mp4" }),
    ).toBeInTheDocument();
  });
  it("filters candidates, saves a shortlist, and removes a saved video", async () => {
    const user = await upload();
    await user.click(
      screen.getByRole("button", { name: "YouTube", exact: true }),
    );
    expect(
      screen.queryByRole("link", { name: "Historic space flight" }),
    ).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Save Rocket launch from the coast" }),
    );
    await user.click(screen.getByRole("button", { name: /Saved videos/ }));
    expect(
      screen.getByRole("link", { name: "Rocket launch from the coast" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export links" })).toBeEnabled();
    await user.click(
      screen.getByRole("button", {
        name: "Unsave Rocket launch from the coast",
      }),
    );
    expect(
      screen.getByText("Your next reference starts with a clip."),
    ).toBeInTheDocument();
  });
  it("compares a real candidate beside the uploaded clip with keyboard dismissal", async () => {
    const user = await upload();
    const trigger = screen.getAllByRole("button", {
      name: "Compare",
      exact: true,
    })[0];
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", {
      name: "Compare video candidate",
    });
    expect(
      within(dialog).getByTitle("Watch Rocket launch from the coast"),
    ).toHaveAttribute(
      "src",
      "https://www.youtube-nocookie.com/embed/abcdefghijk",
    );
    expect(dialog.querySelector("video")).toHaveAttribute(
      "src",
      "blob:clip-preview",
    );
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
  it("lets the user refine a generated description without uploading the file again", async () => {
    const user = await upload();
    await user.click(screen.getByText("Refine the description"));
    const box = screen.getByLabelText("Search description");
    await user.clear(box);
    await user.type(box, "rocket launch at night");
    await user.click(screen.getByRole("button", { name: "Search again" }));
    await screen.findByText("Similar videos to explore");
    expect(fetch).toHaveBeenCalledWith(
      `/api/refine/${jobId}`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ query: "rocket launch at night" }),
      }),
    );
    expect(
      vi
        .mocked(fetch)
        .mock.calls.filter(([url]) => url === "/api/search-video"),
    ).toHaveLength(1);
  });
  it("shows provider failure without inserting saved candidates", async () => {
    vi.mocked(fetch).mockImplementation(async (url) => {
      if (url === "/api/health")
        return {
          ok: true,
          json: async () => ({ mode: "internet-search" }),
        } as Response;
      if (url === "/api/search-video")
        return { ok: true, json: async () => ({ id: jobId }) } as Response;
      return {
        ok: true,
        json: async () => ({
          status: "complete",
          result: {
            ...search,
            results: [],
            warnings: [
              "Live search unavailable. No saved results substituted.",
            ],
          },
        }),
      } as Response;
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Live engine connected");
    await user.upload(
      screen.getByLabelText("Choose a video file"),
      new File(["x"], "clip.mp4", { type: "video/mp4" }),
    );
    await screen.findByText("No video candidates found");
    expect(screen.getByText(/Live search unavailable/)).toBeInTheDocument();
    expect(
      screen.queryByText("Rocket launch from the coast"),
    ).not.toBeInTheDocument();
  });
  it("disables upload when the live service is unavailable, without a demo fallback", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false } as Response);
    render(<App />);
    await screen.findByText("Connect your local search engine");
    expect(
      screen.getByRole("button", { name: "Choose a video" }),
    ).toBeDisabled();
    expect(screen.queryByText(/try a sample/i)).not.toBeInTheDocument();
  });
  it("prevents a second submission while the first request is pending", async () => {
    let resolve!: (r: Response) => void;
    const pending = new Promise<Response>((r) => {
      resolve = r;
    });
    const original = vi.mocked(fetch).getMockImplementation()!;
    vi.mocked(fetch).mockImplementation((url, init) =>
      url === "/api/search-video" ? pending : original(url, init),
    );
    render(<App />);
    await screen.findByText("Live engine connected");
    const drop = screen.getByRole("region", { name: "Submit a video" });
    fireEvent.drop(drop, {
      dataTransfer: { files: [new File(["x"], "one.mp4")] },
    });
    fireEvent.drop(drop, {
      dataTransfer: { files: [new File(["x"], "two.mp4")] },
    });
    expect(
      vi
        .mocked(fetch)
        .mock.calls.filter(([url]) => url === "/api/search-video"),
    ).toHaveLength(1);
    await act(async () =>
      resolve({ ok: true, json: async () => ({ id: jobId }) } as Response),
    );
    await screen.findByText("Similar videos to explore");
  });
  it("reopens a previous user search after a reload", async () => {
    localStorage.setItem("traceback:internet:last-search", jobId);
    const user = userEvent.setup();
    const { container } = render(<App />);
    await user.click(
      await screen.findByRole("button", { name: /Reopen latest search/ }),
    );
    await screen.findByText("Similar videos to explore");
    expect(container.querySelector("video")).toHaveAttribute(
      "src",
      `/api/query/${jobId}`,
    );
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Choose a video" }),
      ).toBeEnabled(),
    );
  });
});
