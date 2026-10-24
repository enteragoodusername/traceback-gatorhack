import { useEffect, useState } from "react";
import {
  ArrowDownToLine,
  CheckCheck,
  ChevronDown,
  ChevronUp,
  FlaskConical,
} from "lucide-react";
import { asset } from "./paths";

type StressCase = {
  id: string;
  description: string;
  results: {
    sourceId: string;
    verifiedFrames: number;
    speed: number;
    speedReliable: boolean;
    timingAmbiguous: boolean;
  }[];
};
type Stress = { complete: boolean; scope: string; cases: StressCase[] };
type Ingestion = {
  newSourceRecovered: boolean;
  falseMatches: number;
  verifiedFrames: number;
  evidenceChecksumsVerified: number;
  speedError: number;
  offsetError: number;
};
type CrossWork = {
  complete: boolean;
  recovered: number;
  positiveCount: number;
  rejected: number;
  negativeCount: number;
  falseMatchCases: number;
  failureNote: string;
  observations: {
    id: string;
    correct: boolean;
    expectedSourceId: string | null;
    returnedSourceIds: string[];
    retrievalRank: number | null;
  }[];
};

export default function Diagnostics() {
  const [stress, setStress] = useState<Stress | null>(null);
  const [ingestion, setIngestion] = useState<Ingestion | null>(null);
  const [open, setOpen] = useState(false);
  const [crossWork, setCrossWork] = useState<CrossWork | null>(null);
  useEffect(() => {
    let active = true;
    const read = async (path: string) => {
      try {
        const response = await fetch(asset(path));
        return response.ok ? await response.json() : null;
      } catch {
        return null;
      }
    };
    void Promise.all([
      read("/validation/live-ingestion.json"),
      read("/validation/stress-cases.json"),
      read("/validation/cross-work.json"),
    ]).then(([live, difficult, additional]) => {
      if (active) {
        setIngestion(live);
        setStress(difficult);
        setCrossWork(additional?.complete ? additional : null);
      }
    });
    return () => {
      active = false;
    };
  }, []);
  if (!stress && !ingestion && !crossWork) return null;
  return (
    <section className="diagnostics panel">
      <header>
        <div>
          <span className="eyebrow">NEW INPUTS. DOCUMENTED LIMITS.</span>
          <h2>
            <FlaskConical size={21} /> More than the bundled examples
          </h2>
        </div>
      </header>
      {ingestion?.newSourceRecovered && (
        <div className="ingestion-check">
          <CheckCheck size={22} />
          <div>
            <h3>A new source, through the actual API.</h3>
            <p>
              A separate Sintel excerpt was uploaded, indexed, searched, and
              recovered from a cropped, mirrored, speed-changed query.{" "}
              {ingestion.verifiedFrames} frames supported the match;{" "}
              {ingestion.evidenceChecksumsVerified} image checksums were
              verified. No extra sources matched.
            </p>
            <a href={asset("/validation/live-ingestion.json")} download>
              <ArrowDownToLine size={13} /> Inspect the recorded HTTP workflow
              result
            </a>
          </div>
        </div>
      )}
      {crossWork && (
        <details className="extended-validation">
          <summary>
            Additional-film test: {crossWork.recovered}/
            {crossWork.positiveCount} edits verified, {crossWork.rejected}/
            {crossWork.negativeCount} negatives rejected
          </summary>
          <p>
            Two new Big Buck Bunny excerpts joined the four bundled sources in
            an isolated library. The engine was unchanged.{" "}
            {crossWork.falseMatchCases} false source matches were returned.
            These cases are separate from the main evaluation.
          </p>
          <p>{crossWork.failureNote}</p>
          <div className="evaluation-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Observed decision</th>
                  <th>Expected source rank</th>
                </tr>
              </thead>
              <tbody>
                {crossWork.observations.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>
                      {row.correct
                        ? row.expectedSourceId
                          ? "Correct source verified"
                          : "Correctly rejected"
                        : row.returnedSourceIds.length
                          ? "Incorrect source decision"
                          : "Abstained on a matching clip"}
                    </td>
                    <td>{row.retrievalRank ?? "No indexed source expected"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <a href={asset("/validation/cross-work.json")} download>
            <ArrowDownToLine size={13} /> Download all additional-film results
          </a>
        </details>
      )}
      {stress && (
        <>
          <button
            className="evaluation-expand"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
          >
            {open
              ? "Hide diagnostic stress cases"
              : `Inspect ${stress.cases.length} difficult or unsupported edits`}
            {open ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
          {open && (
            <div className="stress-cases">
              <p>{stress.scope}</p>
              {!stress.complete && <p>Diagnostic run is incomplete.</p>}
              <div className="evaluation-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Construction</th>
                      <th>Observed behavior</th>
                      <th>Interpretation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stress.cases.map((row) => (
                      <tr key={row.id}>
                        <td>{row.id.replaceAll("-", " ")}</td>
                        <td>
                          {row.results.length
                            ? row.results.map((r) => (
                                <span key={r.sourceId}>
                                  {r.sourceId}: {r.verifiedFrames} verified
                                  frames;{" "}
                                  {r.speedReliable && !r.timingAmbiguous
                                    ? `${r.speed.toFixed(2)}× fitted speed`
                                    : "speed uncertain"}
                                </span>
                              ))
                            : "No verified source"}
                        </td>
                        <td>{row.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <a
                className="diagnostic-download"
                href={asset("/validation/stress-cases.json")}
                download
              >
                <ArrowDownToLine size={14} /> Download every diagnostic result
              </a>
            </div>
          )}
        </>
      )}
    </section>
  );
}
