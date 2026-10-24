import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import axe from "axe-core";
import App from "../src/App";
import { search, jobId } from "./internet-fixture";
const options = {
  iframes: false,
  rules: { "color-contrast": { enabled: false } },
};
it("has accessible structure for upload, results, comparison and saved links", async () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  document.title = "Traceback — Find similar videos";
  document.documentElement.lang = "en";
  URL.createObjectURL = vi.fn(() => "blob:clip");
  URL.revokeObjectURL = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/api/health")
        return { ok: true, json: async () => ({ mode: "internet-search" }) };
      if (url === "/api/search-video")
        return { ok: true, json: async () => ({ id: jobId }) };
      return {
        ok: true,
        json: async () => ({ status: "complete", result: search }),
      };
    }),
  );
  const user = userEvent.setup();
  const { container } = render(<App />);
  await screen.findByText("Live engine connected");
  expect((await axe.run(container, options)).violations).toEqual([]);
  await user.upload(
    screen.getByLabelText("Choose a video file"),
    new File(["video"], "my-clip.mp4", { type: "video/mp4" }),
  );
  await screen.findByText("Similar videos to explore");
  expect((await axe.run(container, options)).violations).toEqual([]);
  await user.click(
    screen.getAllByRole("button", { name: "Compare", exact: true })[0],
  );
  expect((await axe.run(container, options)).violations).toEqual([]);
  await user.keyboard("{Escape}");
  await user.click(screen.getByRole("button", { name: /Saved videos/ }));
  expect((await axe.run(container, options)).violations).toEqual([]);
}, 15000);
