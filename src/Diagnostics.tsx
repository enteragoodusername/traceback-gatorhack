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

export default function Diagnostics() {
  const [stress, setStress] = useState<Stress | null>(null);
  const [ingestion, setIngestion] = useState<Ingestion | null>(null);
  const [open, setOpen] = useState(false);
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
    ]).then(([live, difficult]) => {
      if (active) {
        setIngestion(live);
        setStress(difficult);
      }
    });
    return () => {
      active = false;
    };
  }, []);
  if (!stress && !ingestion) return null;
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
