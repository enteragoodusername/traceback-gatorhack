import { describe, it, expect, vi } from "vitest";
import { webcrypto } from "node:crypto";
import { unzipSync, strFromU8 } from "fflate";
import { createEvidencePacket, digest } from "../src/evidence";
import actualReport from "../public/evidence/vertical/report.json";
import type { Report } from "../src/types";

describe("evidence integrity", () => {
  it("includes every inspected frame and hashes the exact exported report", async () => {
    vi.stubGlobal("crypto", webcrypto);
    const report = structuredClone(actualReport) as Report;
    delete report.evidenceAssets;
    const bytes = new Uint8Array([1, 2, 3, 4]);
    const loader = vi.fn(async () => ({
      ok: true,
      arrayBuffer: async () => bytes.buffer,
    })) as unknown as typeof fetch;
    const packet = unzipSync(
      await createEvidencePacket(
        report,
        "/evidence/",
        "Test attribution",
        loader,
      ),
    );
    const exported = JSON.parse(strFromU8(packet["report.json"]));
    const expected = await digest(packet["report.json"]);
    expect(strFromU8(packet["report.sha256"])).toBe(
      `${expected}  report.json\n`,
    );
    expect(exported.evidenceAssets.length).toBe(
      report.results.reduce((n, m) => n + m.evidence.length * 2, 0),
    );
    for (const asset of exported.evidenceAssets)
      expect(await digest(packet["frames/" + asset.file])).toBe(asset.sha256);
    expect(strFromU8(packet["README.txt"])).toContain("NOT digital signatures");
  });
  it("refuses changed frames rather than silently exporting different evidence", async () => {
    vi.stubGlobal("crypto", webcrypto);
    const report = structuredClone(actualReport) as Report;
    const name = report.results[0].evidence[0].queryImage;
    report.evidenceAssets = [{ file: name, sha256: "0".repeat(64) }];
    const loader = vi.fn(async () => ({
      ok: true,
      arrayBuffer: async () => new Uint8Array([9]).buffer,
    })) as unknown as typeof fetch;
    await expect(
      createEvidencePacket(report, "/evidence/", "", loader),
    ).rejects.toThrow("checksum");
  });
  it("rejects path traversal in a supplied report", async () => {
    const report = structuredClone(actualReport) as Report;
    report.results[0].evidence[0].queryImage = "../secret.jpg";
    await expect(
      createEvidencePacket(report, "/evidence/", ""),
    ).rejects.toThrow("invalid evidence filename");
  });
});
