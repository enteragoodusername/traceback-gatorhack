import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";
import axe from "axe-core";
import TrimClip from "../src/TrimClip";

beforeEach(() => {
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
});
function setup(duration = 120) {
  const onSubmit = vi.fn(),
    onCancel = vi.fn();
  const view = render(
    <TrimClip
      src="/api/input/test"
      filename="long.mp4"
      duration={duration}
      busy={false}
      message=""
      onSubmit={onSubmit}
      onCancel={onCancel}
    />,
  );
  return { ...view, onSubmit, onCancel };
}
it("moves the 60-second window through the entire video and submits only its interval", async () => {
  const { onSubmit } = setup();
  fireEvent.change(screen.getByRole("slider"), { target: { value: "60" } });
  expect(screen.getByLabelText("Start (seconds)")).toHaveValue(60);
  expect(screen.getByLabelText("End (seconds)")).toHaveValue(120);
  expect(onSubmit).not.toHaveBeenCalled();
  await userEvent.click(
    screen.getByRole("button", { name: "Search this clip" }),
  );
  expect(onSubmit).toHaveBeenCalledWith(60, 60);
});
it("allows a shorter precise interval and blocks empty or out-of-bounds selections", async () => {
  const { onSubmit } = setup();
  fireEvent.change(screen.getByLabelText("Start (seconds)"), {
    target: { value: "48.5" },
  });
  fireEvent.change(screen.getByLabelText("End (seconds)"), {
    target: { value: "51.5" },
  });
  await userEvent.click(
    screen.getByRole("button", { name: "Search this clip" }),
  );
  expect(onSubmit).toHaveBeenLastCalledWith(48.5, 3);
  for (const value of ["", "49", "121", "110"]) {
    fireEvent.change(screen.getByLabelText("End (seconds)"), {
      target: { value },
    });
    expect(
      screen.getByRole("button", { name: "Search this clip" }),
    ).toBeDisabled();
  }
});
it("previews the selected interval and pauses playback at its end", async () => {
  const { container } = setup();
  fireEvent.change(screen.getByRole("slider"), { target: { value: "30" } });
  const video = container.querySelector("video")!;
  await userEvent.click(
    screen.getByRole("button", { name: "Preview selection" }),
  );
  expect(video.currentTime).toBe(30);
  expect(video.play).toHaveBeenCalled();
  Object.defineProperty(video, "paused", { configurable: true, value: false });
  video.currentTime = 90;
  fireEvent.timeUpdate(video);
  expect(video.pause).toHaveBeenCalled();
});
it("keeps time selection available when the browser cannot preview the format", async () => {
  const { container, onSubmit } = setup();
  fireEvent.error(container.querySelector("video")!);
  expect(screen.getByRole("status")).toHaveTextContent("Preview unavailable");
  await userEvent.click(
    screen.getByRole("button", { name: "Search this clip" }),
  );
  expect(onSubmit).toHaveBeenCalledWith(0, 60);
});
it("has labeled keyboard controls and no structural accessibility violations", async () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  const { container, onCancel } = setup();
  expect(
    screen.getByRole("heading", { name: "Choose the part to search" }),
  ).toHaveFocus();
  expect(
    (
      await axe.run(container, {
        rules: { "color-contrast": { enabled: false } },
      })
    ).violations,
  ).toEqual([]);
  await userEvent.click(
    screen.getByRole("button", { name: "Choose another video" }),
  );
  expect(onCancel).toHaveBeenCalledOnce();
});

it("accepts a fractional last window without a native number-step mismatch", async () => {
  const { onSubmit } = setup(123.456);
  fireEvent.change(screen.getByRole("slider"), { target: { value: "63.456" } });
  expect(screen.getByLabelText("End (seconds)")).toHaveValue(123.456);
  expect(
    screen.getByRole("button", { name: "Search this clip" }),
  ).toBeEnabled();
  expect(
    (screen.getByLabelText("End (seconds)") as HTMLInputElement).validity.valid,
  ).toBe(true);
  await userEvent.click(
    screen.getByRole("button", { name: "Search this clip" }),
  );
  expect(onSubmit).toHaveBeenCalledWith(63.456, 60);
});
