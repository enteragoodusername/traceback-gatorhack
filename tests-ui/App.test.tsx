import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, it, expect, vi } from "vitest";
import App from "../src/App";
import manifest from "../public/manifest.json";
import actualReport from "../public/evidence/vertical/report.json";
import montageReport from "../public/evidence/montage/report.json";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/manifest.json")
        return { ok: true, json: async () => manifest };
      if (url === "/api/health") return { ok: false };
      if (url.includes("/report.json"))
        return { ok: true, json: async () => actualReport };
      throw Error(`Unexpected fetch ${url}`);
    }),
  );
});

describe("judge demo workflow", () => {
  it("loads real fixture analysis, exposes uncertainty, and changes evidence frames", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("The cropped repost", { selector: "h3" });
    await user.click(screen.getByRole("button", { name: "Find the source" }));
    await screen.findByText("Match verified");
    expect(
      screen.getByText("This does not establish ownership or infringement."),
    ).toBeInTheDocument();
    expect(screen.getByText("RECORDED RUN")).toBeInTheDocument();
    const frames = screen.getAllByRole("button", {
      name: /Inspect frame pair/,
    });
    await user.click(frames[1]);
    expect(screen.getByText(/Frame pair 2/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Feature matches" }));
    expect(
      screen.getByRole("button", { name: "Feature matches" }),
    ).toHaveAttribute("aria-pressed", "false");
  });
  it("clears a previous result when changing the query", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("The cropped repost", { selector: "h3" });
    await user.click(screen.getByRole("button", { name: "Find the source" }));
    await screen.findByText("Match verified");
    await user.click(screen.getByRole("button", { name: /A different look/ }));
    expect(screen.queryByText("Match verified")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Find the source" }),
    ).toBeEnabled();
  });
  it("opens an attributed source and exposes the content hash", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("The cropped repost", { selector: "h3" });
    await user.click(screen.getByRole("button", { name: /Source library/ }));
    await user.click(screen.getByRole("button", { name: /The bridge/ }));
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByText(manifest.sources[0].sha256),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByRole("link", { name: "CC BY 3.0" }),
    ).toHaveAttribute("href", "https://creativecommons.org/licenses/by/3.0/");
    await user.click(
      screen.getByRole("button", { name: "Close source preview" }),
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("describes unavailable sponsor integrations honestly", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Under the hood" }));
    expect(screen.getAllByText("API key required")).toHaveLength(2);
    expect(screen.getByText("Hosted recorded demo")).toBeInTheDocument();
  });
  it("handles missing recorded data with a recoverable error", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("The cropped repost", { selector: "h3" });
    vi.mocked(fetch).mockImplementationOnce(
      async () => ({ ok: false }) as Response,
    );
    await user.click(screen.getByRole("button", { name: "Find the source" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("not available"),
    );
    expect(
      screen.getByRole("button", { name: "Find the source" }),
    ).toBeEnabled();
  });
});

describe("live and negative analysis paths", () => {
  it("uploads a demo to the real API contract and marks the response as live", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url === "/manifest.json")
          return { ok: true, json: async () => manifest };
        if (url === "/api/health")
          return {
            ok: true,
            json: async () => ({
              status: "ok",
              semantic: true,
              gemini: false,
              twinly: false,
            }),
          };
        if (url === "/api/library")
          return {
            ok: true,
            json: async () => ({ sources: manifest.sources }),
          };
        if (url === manifest.demos[0].url)
          return {
            ok: true,
            blob: async () => new Blob(["video"], { type: "video/mp4" }),
          };
        if (url === "/api/analyze")
          return { ok: true, json: async () => ({ id: "live-test" }) };
        if (url === "/api/jobs/live-test")
          return {
            ok: true,
            json: async () => ({
              status: "complete",
              report: { ...actualReport, recorded: false },
            }),
          };
        throw Error(`Unexpected fetch ${url}`);
      }),
    );
    render(<App />);
    await user.click(
      await screen.findByRole("checkbox", {
        name: "Run this demo live on my computer",
      }),
    );
    await user.click(screen.getByRole("button", { name: "Find the source" }));
    expect(
      await screen.findByText("Match verified", {}, { timeout: 4000 }),
    ).toBeInTheDocument();
    expect(screen.queryByText("RECORDED RUN")).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      "/api/analyze",
      expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
    );
  });

  it("renders an abstention without a fabricated source", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("The cropped repost", { selector: "h3" });
    vi.mocked(fetch).mockImplementationOnce(
      async () =>
        ({
          ok: true,
          json: async () => ({ ...actualReport, results: [] }),
        }) as Response,
    );
    await user.click(screen.getByRole("button", { name: "Find the source" }));
    expect(await screen.findByText("No verified match")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Inspect source video" }),
    ).not.toBeInTheDocument();
  });
});

describe("multi-source evidence", () => {
  it("maps both query intervals and switches the inspected source", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      await screen.findByRole("button", { name: /Two stories, one edit/ }),
    );
    vi.mocked(fetch).mockImplementationOnce(
      async () => ({ ok: true, json: async () => montageReport }) as Response,
    );
    await user.click(screen.getByRole("button", { name: "Find the source" }));
    const map = await screen.findByRole("region", {
      name: "Verified source map",
    });
    expect(
      within(map).getByText("2 sources, mapped to your edit."),
    ).toBeInTheDocument();
    await user.click(within(map).getByRole("button", { name: /^The bridge/ }));
    expect(
      screen.getByRole("heading", { name: /The bridge/ }),
    ).toBeInTheDocument();
    expect(
      within(map).getByRole("button", { name: /^The bridge/ }),
    ).toHaveAttribute("aria-pressed", "true");
    await user.click(
      within(map).getByRole("button", { name: /^The laboratory/ }),
    );
    expect(
      screen.getByRole("heading", { name: /The laboratory/ }),
    ).toBeInTheDocument();
  });
});

describe("user-provided source attribution", () => {
  it("shows the uploaded creator instead of the bundled film credit", async () => {
    const user = userEvent.setup();
    const custom = {
      ...manifest.sources[0],
      id: "user-test",
      title: "My original footage",
      creator: "Test Archivist",
      work: "My recording",
      license: "Rights unverified",
      licenseUrl: "",
      sourceUrl: "",
      userProvided: true,
      duration: 15,
      originalOffset: 0,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url === "/manifest.json")
          return { ok: true, json: async () => manifest };
        if (url === "/api/health")
          return {
            ok: true,
            json: async () => ({
              status: "ok",
              semantic: true,
              gemini: false,
              twinly: false,
            }),
          };
        if (url === "/api/library")
          return {
            ok: true,
            json: async () => ({ sources: [...manifest.sources, custom] }),
          };
        return { ok: false };
      }),
    );
    render(<App />);
    await screen.findByText("Local engine connected");
    await user.click(screen.getByRole("button", { name: /Source library/ }));
    await user.click(
      await screen.findByRole("button", { name: /My original footage/ }),
    );
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Test Archivist")).toBeInTheDocument();
    expect(within(dialog).getByText("Source duration")).toBeInTheDocument();
    expect(within(dialog).queryByText(/Blender/)).not.toBeInTheDocument();
  });
});
