import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import axe from "axe-core";
import App from "../src/App";
import manifest from "../public/manifest.json";
import report from "../public/evidence/vertical/report.json";

// DOM checks supplement, but do not claim to replace, visual browser testing.
// jsdom has no layout engine, so contrast must be reviewed in a real browser.
const options = { rules: { "color-contrast": { enabled: false } } };
describe("keyboard and accessible structure", () => {
  it("provides named controls, landmarks and a keyboard-dismissable source dialog", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    document.title = "Traceback — follow the evidence";
    document.documentElement.lang = "en";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url === "/manifest.json")
          return { ok: true, json: async () => manifest };
        if (url === "/api/health") return { ok: false };
        if (url.includes("report.json"))
          return { ok: true, json: async () => report };
        return { ok: false };
      }),
    );
    const user = userEvent.setup();
    const { container } = render(<App />);
    await screen.findByText("The cropped repost", { selector: "h3" });
    expect((await axe.run(container, options)).violations).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Find the source" }));
    await screen.findByText("Match verified");
    expect((await axe.run(container, options)).violations).toEqual([]);
    const trigger = screen.getByRole("button", {
      name: "Inspect source video",
    });
    await user.click(trigger);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect((await axe.run(container, options)).violations).toEqual([]);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  }, 15000);
});
