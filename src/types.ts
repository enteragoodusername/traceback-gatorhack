export type Source = {
  id: string;
  title: string;
  description: string;
  category: string;
  duration: number;
  originalOffset: number;
  url: string;
  thumbnail: string;
  sha256: string;
  creator: string;
  work: string;
  license: string;
  licenseUrl: string;
  sourceUrl: string;
  userProvided?: boolean;
  inputSha256?: string;
};
export type Demo = {
  id: string;
  title: string;
  subtitle: string;
  source: string | null;
  start: number;
  length: number;
  speed: number;
  url: string;
  thumbnail: string;
  sha256: string;
};
export type Manifest = {
  sources: Source[];
  demos: Demo[];
  attribution: string;
  originalUrl: string;
};
export type Evidence = {
  queryTime: number;
  sourceTime: number;
  inliers: number;
  tentative: number;
  inlierRatio: number;
  coverage: number;
  points: { query: [number, number]; source: [number, number] }[];
  quad: [number, number][];
  mirrored: boolean;
  queryImage: string;
  sourceImage: string;
};
export type Alignment = {
  speed: number;
  speedRange?: [number, number];
  speedReliable?: boolean;
  timingAmbiguous?: boolean;
  toleranceSeconds?: number;
  offset: number;
  queryStart: number;
  queryEnd: number;
  sourceStart: number;
  sourceEnd: number;
  support: number;
  residual: number;
  matches: Omit<Evidence, "points" | "quad" | "queryImage" | "sourceImage">[];
};
export type Match = {
  source: Source;
  alignment: Alignment;
  coverage: number;
  medianInliers: number;
  evidence: Evidence[];
  verdict: "strong" | "partial";
};
export type Report = {
  schemaVersion: string;
  engineFingerprint?: string;
  evidenceAssets?: { file: string; sha256: string }[];
  recorded?: boolean;
  fixtureId?: string;
  query: {
    filename: string;
    sha256: string;
    duration: number;
    width: number;
    height: number;
    sampledFrames: number;
  };
  retrieval: {
    engine: string;
    revision: string | null;
    rankings: { sourceId: string; similarity: number; moments: number[] }[];
  };
  results: Match[];
  elapsedSeconds: number;
  method: {
    visual: string;
    temporal: string;
    sourceSampleFps: number;
    querySampleFps: number;
    refinementFps?: number;
    toleranceSeconds: number;
  };
  limitations: string[];
};
