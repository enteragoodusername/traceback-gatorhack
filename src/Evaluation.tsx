import { useEffect, useState } from "react";
import {
  ArrowDownToLine,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Info,
} from "lucide-react";

import { asset } from "./paths";

type Case = {
  id: string;
  source: string | null;
  transform: string;
  found: string[];
  correct: boolean;
  falseMatches: string[];
  offsetError?: number;
  speedError?: number;
  speedReliable?: boolean;
  elapsedSeconds: number;
};
type EvaluationData = {
  suite: string;
  complete: boolean;
  visualOnly: boolean;
  total: number;
  positiveCount: number;
  negativeCount: number;
  recovered: number;
  abstained: number;
  rejected: number;
  falseMatchCases: number;
  medianOffsetError: number | null;
  medianSpeedError: number | null;
  medianLatency: number;
  speedUncertain: number;
  semanticTop1Correct?: number;
  semanticTop1Total?: number;
  maxOffsetError?: number;
  maxSpeedError?: number;
  groups: { name: string; total: number; passed: number }[];
  cases: Case[];
  scope: string;
  limitations: string[];
  hardware: string;
};

export default function Evaluation() {
  const [data, setData] = useState<EvaluationData | null>(null);
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    fetch(asset("/evaluation.json"))
      .then((r) => (r.ok ? r.json() : null))
      .then(setData)
      .catch(() => {});
  }, []);
  if (!data) return null;
  return (
    <section className="evaluation panel">
      <header>
        <div>
          <span className="eyebrow">MEASURED, NOT PROMISED</span>
          <h2>
            <BarChart3 size={21} />
            What we actually tested
          </h2>
        </div>
        <a
          href={asset("/evaluation.json")}
          download="traceback-evaluation.json"
          className="button secondary small"
        >
          <ArrowDownToLine size={14} />
          All results
        </a>
      </header>
      <p className="evaluation-scope">{data.scope}</p>
      <div className="evaluation-label">
        <span className="pill neutral">
          {data.suite.includes("heldout")
            ? "HELD-OUT SUITE"
            : "DEVELOPMENT SUITE"}{" "}
          · {data.total} CASES
        </span>
        <span>
          {data.visualOnly
            ? "Visual verification only"
            : "Full semantic + visual pipeline"}
        </span>
        {!data.complete && <strong>Evaluation in progress</strong>}
      </div>
      <div className="evaluation-metrics">
        <div>
          <strong>
            {data.recovered}
            <em>/{data.positiveCount}</em>
          </strong>
          <span>Edited sources recovered</span>
        </div>
        <div>
          <strong>
            {data.rejected}
            <em>/{data.negativeCount}</em>
          </strong>
          <span>Unrelated clips rejected</span>
        </div>
        <div>
          <strong>{data.falseMatchCases}</strong>
          <span>Cases with a false match</span>
        </div>
        <div>
          <strong>
            {data.medianOffsetError?.toFixed(2) ?? "—"}
            <em>s</em>
          </strong>
          <span>Median start-time error</span>
        </div>
      </div>
      {data.semanticTop1Total !== undefined && data.semanticTop1Total > 0 && (
        <p className="evaluation-retrieval">
          <strong>Qwen retrieval:</strong> the correct source ranked first for{" "}
          {data.semanticTop1Correct}/{data.semanticTop1Total} positive clips.
          All four sources still received visual verification in this
          small-library experiment.
        </p>
      )}
      <div className="evaluation-bars">
        {data.groups.map((group) => (
          <div key={group.name}>
            <label>{group.name.replaceAll("-", " ")}</label>
            <span>
              <i style={{ width: (group.passed / group.total) * 100 + "%" }} />
            </span>
            <strong>
              {group.passed}/{group.total}
            </strong>
          </div>
        ))}
      </div>
      <div className="evaluation-caveat">
        <Info size={16} />
        <p>
          This is a small, controlled test, not a production accuracy claim.
          Timing errors include only recovered sources. {data.abstained}{" "}
          positive clips were not recovered.{" "}
          {data.speedUncertain > 0
            ? data.speedUncertain +
              " recovered clips had uncertain speed estimates."
            : ""}{" "}
          Median runtime: {data.medianLatency}s on a CPU; concurrent work
          affects timing.{" "}
          {data.maxOffsetError !== undefined && (
            <>
              Largest recovered start-time error:{" "}
              {data.maxOffsetError.toFixed(2)}s. Largest playback-speed error:{" "}
              {data.maxSpeedError?.toFixed(3)}×.
            </>
          )}
        </p>
      </div>
      <button
        className="evaluation-expand"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        {expanded ? "Hide individual cases" : "Inspect every test case"}
        {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
      </button>
      {expanded && (
        <div>
          <figure className="timing-figure">
            <a
              href={asset("/evaluation-timing.svg")}
              target="_blank"
              rel="noreferrer"
              aria-label="Open full-size timing-error figure"
            >
              <img
                src={asset("/evaluation-timing.svg")}
                alt="Start-time and playback-speed errors for each recovered positive test case, grouped by edit type"
                loading="lazy"
              />
            </a>
            <figcaption>
              Every recovered positive case is plotted; these are errors against
              known synthetic edit settings.
            </figcaption>
          </figure>
          <div className="evaluation-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Outcome</th>
                  <th>Offset error</th>
                  <th>Speed error</th>
                </tr>
              </thead>
              <tbody>
                {data.cases.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>
                      {row.correct && !row.falseMatches.length
                        ? "Expected result"
                        : row.found.length
                          ? "Unexpected match"
                          : "Abstained"}
                    </td>
                    <td>
                      {row.offsetError === undefined
                        ? "—"
                        : row.offsetError.toFixed(3) + "s"}
                    </td>
                    <td>
                      {row.speedError === undefined
                        ? "—"
                        : row.speedError.toFixed(3) + "×"}
                      {row.speedReliable === false ? " (uncertain)" : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
