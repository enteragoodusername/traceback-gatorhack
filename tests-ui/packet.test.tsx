import { beforeEach, describe, expect, it, vi } from "vitest";
import { webcrypto } from "node:crypto";
import { readFileSync } from "node:fs";
import { strToU8, unzipSync, zipSync } from "fflate";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { verifyEvidencePacket } from "../src/packet";
import { digest, createEvidencePacket } from "../src/evidence";
import unrelated from "../public/evidence/unrelated/report.json";
import type { Report } from "../src/types";
import PacketReview from "../src/PacketReview";
import axe from "axe-core";

const actual = new Uint8Array(
  readFileSync("public/downloads/traceback-evidence.zip"),
);
beforeEach(() => {
  vi.stubGlobal("crypto", webcrypto);
});

async function rewriteReport(update: (report: Record<string, any>) => void) {
  const files = unzipSync(actual);
  const report = JSON.parse(new TextDecoder().decode(files["report.json"]));
  update(report);
  files["report.json"] = strToU8(JSON.stringify(report));
  files["report.sha256"] = strToU8(await digest(files["report.json"]));
  return zipSync(files, { level: 0 });
}

describe("independent packet verification", () => {
  it("verifies the actual published packet and its twelve JPEG frames", async () => {
    const result = await verifyEvidencePacket(actual);
    expect(result.imageCount).toBe(12);
    expect(result.matches).toHaveLength(1);
    expect(result.matches[0].title).toContain("bridge");
    expect(result.matches[0].pairs).toHaveLength(6);
    expect(result.reportHash).toHaveLength(64);
  });
  it("refuses a changed image even when the ZIP itself is valid", async () => {
    const files = unzipSync(actual);
    const name = Object.keys(files).find((n) => n.startsWith("frames/"))!;
    files[name][files[name].length - 10] ^= 1;
    await expect(verifyEvidencePacket(zipSync(files))).rejects.toThrow(
      "Image checksum mismatch",
    );
  });
  it("refuses a report changed without updating its checksum", async () => {
    const files = unzipSync(actual);
    files["report.json"] = strToU8("{}");
    await expect(verifyEvidencePacket(zipSync(files))).rejects.toThrow(
      "Report checksum mismatch",
    );
  });
  it("rejects an incomplete inventory despite a recomputed report hash", async () => {
    const changed = await rewriteReport((r) => {
      r.evidenceAssets.pop();
    });
    await expect(verifyEvidencePacket(changed)).rejects.toThrow("inventory");
  });
  it("rejects hidden files and path traversal entries", async () => {
    const files = unzipSync(actual);
    files["../unexpected.txt"] = strToU8("test");
    await expect(verifyEvidencePacket(zipSync(files))).rejects.toThrow(
      "unexpected file",
    );
  });
  it("rejects an oversized advertised expansion before decompressing", async () => {
    const bytes = new Uint8Array(actual);
    const view = new DataView(bytes.buffer);
    for (let i = 0; i < bytes.length - 46; i++) {
      if (view.getUint32(i, true) === 0x02014b50) {
        view.setUint32(i + 24, 200 * 1024 * 1024, true);
        break;
      }
    }
    await expect(verifyEvidencePacket(bytes)).rejects.toThrow(
      "Unsupported ZIP entry",
    );
  });
  it("rejects malformed measurements rather than crashing the viewer", async () => {
    const changed = await rewriteReport((r) => {
      r.results[0].alignment.speed = "fast";
    });
    await expect(verifyEvidencePacket(changed)).rejects.toThrow(
      "invalid measurement",
    );
  });
  it("accepts a consistently updated packet without claiming authentication", async () => {
    const changed = await rewriteReport((r) => {
      r.query.filename = "renamed-by-someone.mp4";
    });
    expect((await verifyEvidencePacket(changed)).filename).toBe(
      "renamed-by-someone.mp4",
    );
  });
  it("verifies an abstention packet without inventing evidence images", async () => {
    const loader = vi.fn();
    const bytes = await createEvidencePacket(
      unrelated as Report,
      "/evidence/",
      "",
      loader,
    );
    const result = await verifyEvidencePacket(bytes);
    expect(result.matches).toEqual([]);
    expect(result.imageCount).toBe(0);
    expect(loader).not.toHaveBeenCalled();
  });
  it("rejects duplicate ZIP names before decoding either copy", async () => {
    const bytes = new Uint8Array(actual);
    const oldName = new TextEncoder().encode("frames/bridge-0-query.jpg");
    const newName = new TextEncoder().encode("frames/bridge-1-query.jpg");
    let changed = 0;
    for (let i = 0; i <= bytes.length - oldName.length; i++) {
      if (oldName.every((b, j) => bytes[i + j] === b)) {
        bytes.set(newName, i);
        changed++;
      }
    }
    expect(changed).toBe(2);
    await expect(verifyEvidencePacket(bytes)).rejects.toThrow(
      "duplicate ZIP entries",
    );
  });
  it("compares original query bytes locally and distinguishes a different file", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, arrayBuffer: async () => actual.buffer })),
    );
    vi.stubGlobal(
      "URL",
      class extends URL {
        static createObjectURL() {
          return "blob:test-frame";
        }
        static revokeObjectURL() {}
      },
    );
    const user = userEvent.setup();
    render(<PacketReview />);
    await user.click(
      screen.getByRole("button", { name: "Verify sample packet" }),
    );
    await screen.findByText("Report + 12 frame checksums match.");
    const input = screen.getByLabelText("Compare original query file");
    const original = new Uint8Array(
      readFileSync("public/media/query-vertical.mp4"),
    );
    const file = new File([original.buffer], "original.mp4", {
      type: "video/mp4",
    });
    Object.defineProperty(file, "arrayBuffer", {
      value: async () => original.buffer,
    });
    await user.upload(input, file);
    expect(
      await screen.findByText(
        "Query bytes match the SHA-256 recorded in this packet.",
      ),
    ).toBeInTheDocument();
    const other = new File(["different bytes"], "different.mp4", {
      type: "video/mp4",
    });
    Object.defineProperty(other, "arrayBuffer", {
      value: async () => new TextEncoder().encode("different bytes").buffer,
    });
    await user.upload(input, other);
    expect(
      await screen.findByText(/This file has a different SHA-256/),
    ).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("shows a local verification result and lets readers inspect frame pairs", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, arrayBuffer: async () => actual.buffer })),
    );
    vi.stubGlobal(
      "URL",
      class extends URL {
        static createObjectURL() {
          return "blob:test-frame";
        }
        static revokeObjectURL() {}
      },
    );
    const user = userEvent.setup();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    document.title = "Traceback packet review";
    document.documentElement.lang = "en";
    const { container } = render(
      <main>
        <PacketReview />
      </main>,
    );
    await user.click(
      screen.getByRole("button", { name: "Verify sample packet" }),
    );
    expect(
      await screen.findByText("Report + 12 frame checksums match."),
    ).toBeInTheDocument();
    expect(screen.getByText(/Analysis was not rerun/)).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Review included pair 2" }),
    );
    expect(screen.getByText(/Pair 2 of 6/)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(
      (
        await axe.run(container, {
          rules: { "color-contrast": { enabled: false } },
        })
      ).violations,
    ).toEqual([]);
  });
});
