import { strToU8, zipSync } from "fflate";
import type { Report } from "./types";

export async function digest(bytes: Uint8Array): Promise<string> {
  const buffer = new Uint8Array(bytes).buffer;
  const hash = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(hash)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function createEvidencePacket(
  report: Report,
  base: string,
  attribution: string,
  fetcher: typeof fetch = fetch,
): Promise<Uint8Array> {
  const filenames = [
    ...new Set(
      report.results.flatMap((result) =>
        result.evidence.flatMap((e) => [e.queryImage, e.sourceImage]),
      ),
    ),
  ];
  if (filenames.some((name) => !/^[-a-zA-Z0-9]+\.jpg$/.test(name)))
    throw Error("The report contains an invalid evidence filename.");
  const archive: Record<string, Uint8Array> = {};
  const checksums: { file: string; sha256: string }[] = [];
  for (const filename of filenames) {
    const response = await fetcher(base + filename);
    if (!response.ok)
      throw Error(
        "An evidence image could not be downloaded. Please try exporting again.",
      );
    const bytes = new Uint8Array(await response.arrayBuffer());
    const sha256 = await digest(bytes);
    const expected = report.evidenceAssets?.find(
      (asset) => asset.file === filename,
    )?.sha256;
    if (expected && sha256 !== expected)
      throw Error(
        "An evidence image changed since analysis. Export stopped because its checksum does not match.",
      );
    archive["frames/" + filename] = bytes;
    checksums.push({ file: filename, sha256 });
  }
  const exported = {
    ...report,
    evidenceAssets: checksums,
    exportedAt: new Date().toISOString(),
    attribution,
  };
  const data = strToU8(JSON.stringify(exported, null, 2));
  archive["report.json"] = data;
  archive["report.sha256"] = strToU8(`${await digest(data)}  report.json\n`);
  archive["README.txt"] = strToU8(
    `TRACEBACK EVIDENCE PACKET\n\nThis packet contains actual visual correspondence measurements and the inspected frame pairs.\n\nFiles:\n- report.json: query/source hashes, model revision, alignment, matching points, limitations.\n- frames/: query and source evidence images.\n- report.sha256: checksum of report.json.\n\nVerify with the project's scripts/verify_packet.py. Image SHA-256 checksums are recorded in report.json. The original videos are not included; their hashes identify the analyzed files.\n\nChecksums detect accidental changes. They are NOT digital signatures and do not prove who created a file, when it was published, who owns it, or whether reuse is lawful. A person who replaces both data and checksums can create a different internally consistent packet.\n\n${attribution}\n\n${report.limitations.join("\n")}\n`,
  );
  return zipSync(archive, { level: 0 });
}
