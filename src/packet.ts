import { strFromU8, unzipSync } from "fflate";
import { digest } from "./evidence";

const MAX_PACKET = 32 * 1024 * 1024;
const MAX_EXPANDED = 64 * 1024 * 1024;
const HASH = /^[a-f0-9]{64}$/;
const FRAME = /^[-a-zA-Z0-9]+\.jpg$/;

export type PacketPair = {
  queryImage: string;
  sourceImage: string;
  queryTime: number;
  sourceTime: number;
  inliers: number;
};
export type PacketMatch = {
  title: string;
  creator: string;
  license: string;
  sourceHash: string;
  sourceStart: number;
  sourceEnd: number;
  speed: number;
  speedReliable: boolean;
  support: number;
  pairs: PacketPair[];
};
export type PacketReview = {
  packetHash: string;
  reportHash: string;
  filename: string;
  queryHash: string;
  model: string;
  modelRevision: string;
  engineFingerprint: string;
  matches: PacketMatch[];
  images: Record<string, Uint8Array>;
  imageCount: number;
  limitations: string[];
};

/** Check the ZIP directory before allocating decompressed data. ZIP64 is unnecessary here. */
function inspectArchive(bytes: Uint8Array) {
  if (bytes.length > MAX_PACKET)
    throw Error("Choose a packet smaller than 32 MB.");
  if (bytes.length < 22) throw Error("This is not a complete ZIP packet.");
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let end = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
    if (
      view.getUint32(i, true) === 0x06054b50 &&
      i + 22 + view.getUint16(i + 20, true) === bytes.length
    ) {
      end = i;
      break;
    }
  }
  if (end < 0) throw Error("The ZIP directory is missing or incomplete.");
  const count = view.getUint16(end + 10, true);
  const size = view.getUint32(end + 12, true);
  let offset = view.getUint32(end + 16, true);
  if (
    view.getUint16(end + 4, true) ||
    view.getUint16(end + 6, true) ||
    view.getUint16(end + 8, true) !== count ||
    count > 1000 ||
    offset + size !== end
  )
    throw Error("Unsupported or oversized ZIP directory.");
  const names = new Set<string>();
  let expanded = 0;
  for (let i = 0; i < count; i++) {
    if (offset + 46 > end || view.getUint32(offset, true) !== 0x02014b50)
      throw Error("Malformed ZIP directory.");
    const flags = view.getUint16(offset + 8, true);
    const compression = view.getUint16(offset + 10, true);
    const compressed = view.getUint32(offset + 20, true);
    const original = view.getUint32(offset + 24, true);
    const nameLength = view.getUint16(offset + 28, true);
    const next =
      offset +
      46 +
      nameLength +
      view.getUint16(offset + 30, true) +
      view.getUint16(offset + 32, true);
    const local = view.getUint32(offset + 42, true);
    if (
      next > end ||
      flags & 1 ||
      ![0, 8].includes(compression) ||
      original > MAX_EXPANDED ||
      local + 30 > offset
    )
      throw Error("Unsupported ZIP entry.");
    const name = strFromU8(
      bytes.subarray(offset + 46, offset + 46 + nameLength),
    );
    if (names.has(name)) throw Error("Packet contains duplicate ZIP entries.");
    if (
      !["report.json", "report.sha256", "README.txt"].includes(name) &&
      !/^frames\/[-a-zA-Z0-9]+\.jpg$/.test(name)
    )
      throw Error("Packet contains an unexpected file.");
    if (view.getUint32(local, true) !== 0x04034b50)
      throw Error("Malformed ZIP file header.");
    const localNameLength = view.getUint16(local + 26, true);
    const dataStart =
      local + 30 + localNameLength + view.getUint16(local + 28, true);
    const localName = strFromU8(
      bytes.subarray(local + 30, local + 30 + localNameLength),
    );
    if (localName !== name || dataStart + compressed > offset)
      throw Error("ZIP entry boundaries do not match.");
    expanded += original;
    if (expanded > MAX_EXPANDED)
      throw Error("Expanded packet exceeds the 64 MB limit.");
    if (name === "report.json" && original > 2 * 1024 * 1024)
      throw Error("Evidence report exceeds the 2 MB limit.");
    names.add(name);
    offset = next;
  }
  if (
    offset !== end ||
    !names.has("report.json") ||
    !names.has("report.sha256")
  )
    throw Error("The packet is missing its report or checksum.");
  return names;
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw Error("The evidence report has an invalid structure.");
  return value as Record<string, unknown>;
}
function text(value: unknown, limit = 1000): string {
  if (typeof value !== "string" || value.length > limit)
    throw Error("The evidence report contains invalid text.");
  return value;
}
function number(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value))
    throw Error("The evidence report contains an invalid measurement.");
  return value;
}
function hash(value: unknown): string {
  const result = text(value, 64);
  if (!HASH.test(result))
    throw Error("The evidence report contains an invalid checksum.");
  return result;
}
function array(value: unknown, limit = 1000): unknown[] {
  if (!Array.isArray(value) || value.length > limit)
    throw Error("The evidence report contains an invalid inventory.");
  return value;
}

/** Local integrity verification only. It does not authenticate or rerun the analysis. */
export async function verifyEvidencePacket(
  bytes: Uint8Array,
): Promise<PacketReview> {
  const names = inspectArchive(bytes);
  let files: Record<string, Uint8Array>;
  try {
    files = unzipSync(bytes);
  } catch {
    throw Error("The ZIP data could not be decoded.");
  }
  const raw = files["report.json"];
  const reportHash = await digest(raw);
  const expected = strFromU8(files["report.sha256"]).trim().split(/\s+/)[0];
  if (!HASH.test(expected) || reportHash !== expected)
    throw Error(
      "Report checksum mismatch. The report changed or its checksum is incorrect.",
    );
  let parsed: unknown;
  try {
    parsed = JSON.parse(strFromU8(raw));
  } catch {
    throw Error("The evidence report is not valid JSON.");
  }
  const report = object(parsed);
  if (report.schemaVersion !== "1.1")
    throw Error("This viewer supports Traceback evidence schema 1.1.");
  const query = object(report.query);
  const retrieval = object(report.retrieval);
  const referenced = new Set<string>();
  const matches = array(report.results, 100).map((value): PacketMatch => {
    const result = object(value),
      source = object(result.source),
      alignment = object(result.alignment);
    const pairs = array(result.evidence, 100).map((value): PacketPair => {
      const pair = object(value);
      const queryImage = text(pair.queryImage),
        sourceImage = text(pair.sourceImage);
      if (!FRAME.test(queryImage) || !FRAME.test(sourceImage))
        throw Error("Unexpected evidence filename.");
      referenced.add(queryImage);
      referenced.add(sourceImage);
      return {
        queryImage,
        sourceImage,
        queryTime: number(pair.queryTime),
        sourceTime: number(pair.sourceTime),
        inliers: number(pair.inliers),
      };
    });
    return {
      title: text(source.title),
      creator: text(source.creator),
      license: text(source.license),
      sourceHash: hash(source.sha256),
      sourceStart: number(alignment.sourceStart),
      sourceEnd: number(alignment.sourceEnd),
      speed: number(alignment.speed),
      speedReliable:
        alignment.speedReliable === true && alignment.timingAmbiguous !== true,
      support: number(alignment.support),
      pairs,
    };
  });
  const inventory = array(report.evidenceAssets);
  const images: Record<string, Uint8Array> = Object.create(null);
  for (const value of inventory) {
    const item = object(value),
      name = text(item.file);
    if (
      !FRAME.test(name) ||
      !referenced.has(name) ||
      Object.hasOwn(images, name)
    )
      throw Error("Evidence inventory does not match the inspected frames.");
    const data = files["frames/" + name];
    if (!data) throw Error(`Missing evidence image: ${name}`);
    if ((await digest(data)) !== hash(item.sha256))
      throw Error(
        `Image checksum mismatch: ${name}. This frame changed or its checksum is incorrect.`,
      );
    if (
      data.length < 3 ||
      data[0] !== 0xff ||
      data[1] !== 0xd8 ||
      data[2] !== 0xff
    )
      throw Error(`Evidence image is not a JPEG: ${name}`);
    images[name] = data;
  }
  if (
    inventory.length !== referenced.size ||
    [...names].filter((n) => n.startsWith("frames/")).length !==
      inventory.length
  )
    throw Error("Evidence inventory does not match the included frames.");
  return {
    packetHash: await digest(bytes),
    reportHash,
    filename: text(query.filename),
    queryHash: hash(query.sha256),
    model: text(retrieval.engine),
    modelRevision:
      retrieval.revision === null ? "Not provided" : text(retrieval.revision),
    engineFingerprint: hash(report.engineFingerprint),
    matches,
    images,
    imageCount: inventory.length,
    limitations: array(report.limitations, 100).map((v) => text(v, 4000)),
  };
}
