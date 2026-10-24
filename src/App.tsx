import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronRight,
  Clock3,
  ExternalLink,
  FileVideo,
  Film,
  FlaskConical,
  Focus,
  FolderOpen,
  GitBranch,
  Info,
  Layers3,
  LoaderCircle,
  Pause,
  Play,
  ScanLine,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import type { Demo, Evidence, Manifest, Match, Report, Source } from "./types";
import Library from "./Library";
import Evaluation from "./Evaluation";
import Diagnostics from "./Diagnostics";
import { createEvidencePacket } from "./evidence";
import { asset } from "./paths";

const time = (n: number) =>
  `${Math.floor(Math.max(0, n) / 60)
    .toString()
    .padStart(2, "0")}:${(Math.max(0, n) % 60).toFixed(1).padStart(4, "0")}`;
const shortTime = (n: number) =>
  `${Math.floor(Math.max(0, n) / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(Math.max(0, n) % 60)
    .toString()
    .padStart(2, "0")}`;
type Page = "trace" | "library" | "method";
type Health = {
  status: string;
  semantic: boolean;
  gemini: boolean;
  twinly: boolean;
};

function App() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [page, setPage] = useState<Page>("trace");
  const [demo, setDemo] = useState<Demo | null>(null);
  const [upload, setUpload] = useState<File | null>(null);
  const [uploadUrl, setUploadUrl] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [base, setBase] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [activeMatch, setActiveMatch] = useState(0);
  const [activeEvidence, setActiveEvidence] = useState(0);
  const [showFeatures, setShowFeatures] = useState(true);
  const [toast, setToast] = useState("");
  const [exporting, setExporting] = useState(false);
  const [liveRun, setLiveRun] = useState(false);
  const [inspectSource, setInspectSource] = useState<Source | null>(null);
  const [inspectTime, setInspectTime] = useState(0);
  const modal = useRef<HTMLElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const [explanation, setExplanation] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const queryVideo = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const requestId = useRef(0);
  useEffect(() => {
    let active = true;
    async function init() {
      try {
        const response = await fetch(asset("/manifest.json"));
        if (!response.ok) throw Error("Could not load the source library.");
        const raw: Manifest = await response.json();
        const m: Manifest = {
          ...raw,
          sources: raw.sources.map((s) => ({
            ...s,
            url: asset(s.url),
            thumbnail: asset(s.thumbnail),
          })),
          demos: raw.demos.map((d) => ({
            ...d,
            url: asset(d.url),
            thumbnail: asset(d.thumbnail),
          })),
        };
        if (!active) return;
        setManifest(m);
        setDemo(m.demos[0]);
        try {
          const r = await fetch("/api/health", {
            signal: AbortSignal.timeout(3000),
          });
          const h = r.ok ? await r.json() : null;
          if (active && h?.status === "ok") {
            setHealth(h);
            const lib = await fetch("/api/library");
            if (lib.ok) {
              const data = await lib.json();
              if (active) setManifest({ ...m, sources: data.sources });
            }
          }
        } catch {
          /* Hosted demo works without a local server. */
        }
      } catch (e) {
        if (active)
          setError(
            e instanceof Error ? e.message : "Could not load the library.",
          );
      }
    }
    void init();
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!inspectSource) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setInspectSource(null);
        returnFocus.current?.focus();
      }
      if (event.key === "Tab" && modal.current) {
        const controls = modal.current.querySelectorAll<HTMLElement>(
          "button,a[href],video[controls]",
        );
        const first = controls[0],
          last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [inspectSource]);
  function openSource(source: Source, start = 0) {
    returnFocus.current = document.activeElement as HTMLElement;
    setInspectTime(start);
    setInspectSource(source);
  }
  function closeSource() {
    setInspectSource(null);
    returnFocus.current?.focus();
  }
  useEffect(() => {
    if (!upload) return;
    const url = URL.createObjectURL(upload);
    setUploadUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [upload]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(t);
  }, [toast]);
  const clear = () => {
    requestId.current++;
    setReport(null);
    setActiveMatch(0);
    setActiveEvidence(0);
    setError("");
    setExplanation("");
    setPlaying(false);
  };
  const chooseDemo = (d: Demo) => {
    clear();
    setUpload(null);
    setDemo(d);
  };
  const chooseFile = (file?: File) => {
    if (!file) return;
    if (file.size > 100 * 1024 * 1024) {
      setError("Choose a video smaller than 100 MB.");
      return;
    }
    if (
      !file.type.startsWith("video/") &&
      !/\.(mp4|mov|webm|mkv)$/i.test(file.name)
    ) {
      setError("Choose an MP4, MOV, WebM, or MKV video.");
      return;
    }
    clear();
    setUpload(file);
  };
  async function runTrace() {
    if (!demo && !upload) return;
    const id = ++requestId.current;
    setBusy(true);
    setError("");
    setExplanation("");
    setReport(null);
    try {
      if (upload || (liveRun && health && demo)) {
        if (!health)
          throw Error(
            "New uploads need the local analysis server. Run ./start.sh in the project, then open its local URL. The hosted demo contains recorded, reproducible analyses.",
          );
        setStage("Uploading your clip");
        const form = new FormData();
        if (upload) form.append("file", upload);
        else if (demo) {
          const response = await fetch(demo.url);
          if (!response.ok)
            throw Error("Could not load the demo video for a live run.");
          form.append(
            "file",
            new File([await response.blob()], demo.id + ".mp4", {
              type: "video/mp4",
            }),
          );
        }
        const res = await fetch("/api/analyze", { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) throw Error(data.detail || "Could not start analysis.");
        while (id === requestId.current) {
          await new Promise((resolve) => setTimeout(resolve, 1000));
          const poll = await fetch(`/api/jobs/${data.id}`);
          if (!poll.ok) throw Error("Analysis session could not be read.");
          const job = await poll.json();
          setStage(job.message || "Analyzing your clip");
          if (job.status === "failed")
            throw Error(job.error || "Analysis failed.");
          if (job.status === "complete") {
            setReport(job.report);
            setBase(`/api/evidence/${data.id}/`);
            break;
          }
        }
      } else if (demo) {
        setStage("Loading a recorded model run");
        const res = await fetch(asset(`/evidence/${demo.id}/report.json`));
        if (!res.ok) throw Error("This demo analysis is not available yet.");
        const data: Report = await res.json();
        if (id === requestId.current) {
          setReport({
            ...data,
            results: data.results.map((result) => ({
              ...result,
              source: {
                ...result.source,
                url: asset(result.source.url),
                thumbnail: asset(result.source.thumbnail),
              },
            })),
          });
          setBase(asset(`/evidence/${demo.id}/`));
        }
      }
      setActiveEvidence(0);
      setActiveMatch(0);
    } catch (e) {
      if (id === requestId.current)
        setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      if (id === requestId.current) setBusy(false);
    }
  }
  async function exportReport() {
    if (!report || exporting) return;
    setExporting(true);
    try {
      const bytes = await createEvidencePacket(
        report,
        base,
        manifest?.attribution || "",
      );
      const blob = new Blob([new Uint8Array(bytes).buffer], {
        type: "application/zip",
      });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `traceback-${report.fixtureId || "analysis"}-evidence.zip`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      setToast("Evidence packet downloaded with frame checksums");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evidence export failed.");
    } finally {
      setExporting(false);
    }
  }
  async function explain() {
    if (!report || !health?.gemini) return;
    setExplanation("Preparing a grounded explanation…");
    try {
      const r = await fetch("/api/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ report }),
      });
      const data = await r.json();
      if (!r.ok) throw Error(data.detail || "Explanation unavailable.");
      setExplanation(data.text);
    } catch (e) {
      setExplanation(
        e instanceof Error ? e.message : "Explanation unavailable.",
      );
    }
  }
  const match = report?.results[activeMatch];
  const evidence = match?.evidence[activeEvidence];
  const queryUrl = upload ? uploadUrl : demo?.url;
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to workspace
      </a>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("trace");
          }}
          aria-label="Traceback home"
        >
          <span className="brand-icon">
            <ScanLine size={24} />
          </span>
          traceback<span className="brand-dot">.</span>
        </a>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          <button
            className={page === "trace" ? "nav-item active" : "nav-item"}
            aria-current={page === "trace" ? "page" : undefined}
            onClick={() => setPage("trace")}
          >
            <ScanLine size={18} />
            Trace a clip<span className="nav-key">↗</span>
          </button>
          <button
            className={page === "library" ? "nav-item active" : "nav-item"}
            aria-current={page === "library" ? "page" : undefined}
            onClick={() => setPage("library")}
          >
            <FolderOpen size={18} />
            Source library
            <span className="nav-count">{manifest?.sources.length || 0}</span>
          </button>
          <button
            className={page === "method" ? "nav-item active" : "nav-item"}
            aria-current={page === "method" ? "page" : undefined}
            onClick={() => setPage("method")}
          >
            <FlaskConical size={18} />
            Under the hood
          </button>
        </nav>
        <div className="sidebar-note">
          <div className="orbit-mark">
            <GitBranch size={25} />
          </div>
          <h3>A source. Not a guess.</h3>
          <p>Follow the visual evidence back to where a clip began.</p>
          <button onClick={() => setPage("method")}>
            How tracing works <ArrowUpRight size={14} />
          </button>
          <a
            className="watch-demo-link"
            href={asset("/demo/")}
            target="_blank"
            rel="noreferrer"
          >
            Watch the walkthrough <Play size={13} />
          </a>
        </div>
        <div className="sidebar-bottom">
          <span className="live-dot" />
          <div>
            <strong>
              {health ? "Local engine connected" : "Interactive demo"}
            </strong>
            <small>
              {health
                ? "Private, on-device retrieval"
                : "Recorded runs · real evidence"}
            </small>
          </div>
          <span className="version">v0.1</span>
        </div>
      </aside>
      <main className="main" id="main-content" tabIndex={-1}>
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />
            <span>
              {page === "trace"
                ? "Trace a clip"
                : page === "library"
                  ? "Source library"
                  : "Under the hood"}
            </span>
          </div>
          <div className="topbar-right">
            <span className="event-badge">
              <span />
              GATOR HACK V
            </span>
            <a
              href="https://arxiv.org/abs/2601.04720"
              target="_blank"
              rel="noreferrer"
              className="model-chip"
            >
              <Sparkles size={14} />
              Built on the frontier
              <ArrowUpRight size={12} />
            </a>
          </div>
        </header>
        <div className="page-content">
          {page === "trace" && (
            <>
              <section className="page-heading">
                <div>
                  <div className="eyebrow">
                    <span className="tiny-line" />
                    VIDEO PROVENANCE, MADE VISIBLE
                  </div>
                  <h1>Every frame has a story.</h1>
                  <p>
                    Find the source behind the edit. Follow the evidence, frame
                    by frame.
                  </p>
                </div>
                <button
                  className="button secondary export-top"
                  disabled={!report || exporting}
                  onClick={exportReport}
                >
                  {exporting ? (
                    <LoaderCircle size={16} className="spin" />
                  ) : (
                    <ArrowDownToLine size={16} />
                  )}
                  <span>{exporting ? "Packaging…" : "Export evidence"}</span>
                </button>
              </section>
              <div className="workbench">
                <section className="query-panel panel">
                  <div className="panel-heading">
                    <div>
                      <span className="step-number">01</span>
                      <h2>Your clip</h2>
                    </div>
                    <span className="micro-label">THE QUESTION</span>
                  </div>
                  <div
                    className="query-video-wrap"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      if (!busy) chooseFile(e.dataTransfer.files[0]);
                    }}
                  >
                    {queryUrl && (
                      <video
                        ref={queryVideo}
                        key={queryUrl}
                        src={queryUrl}
                        poster={!upload ? demo?.thumbnail : undefined}
                        muted
                        loop
                        playsInline
                        preload="metadata"
                        onPlay={() => setPlaying(true)}
                        onPause={() => setPlaying(false)}
                      />
                    )}
                    <span className="video-badge">
                      <FileVideo size={12} />
                      {upload ? "YOUR UPLOAD" : "EDITED EXCERPT"}
                    </span>
                    <button
                      className="play-button"
                      aria-label={
                        playing ? "Pause query clip" : "Play query clip"
                      }
                      onClick={() => {
                        const v = queryVideo.current;
                        if (v) {
                          if (v.paused)
                            void v
                              .play()
                              .catch(() =>
                                setError(
                                  "Your browser could not play this video.",
                                ),
                              );
                          else v.pause();
                        }
                      }}
                    >
                      {playing ? (
                        <Pause size={20} fill="currentColor" />
                      ) : (
                        <Play size={20} fill="currentColor" />
                      )}
                    </button>
                    <span className="video-duration">
                      {upload
                        ? "New clip"
                        : demo
                          ? `${(demo.length / demo.speed).toFixed(1)}s`
                          : ""}
                    </span>
                  </div>
                  <div className="query-details">
                    <div className="file-icon">
                      <Film size={19} />
                    </div>
                    <div>
                      <h3>
                        {upload ? upload.name : demo?.title || "Loading demo…"}
                      </h3>
                      <p>
                        {upload
                          ? `${(upload.size / 1024 / 1024).toFixed(1)} MB · Ready to analyze`
                          : demo?.subtitle}
                      </p>
                    </div>
                  </div>
                  <div className="query-actions">
                    {health && !upload && (
                      <label className="live-run-toggle">
                        <input
                          type="checkbox"
                          checked={liveRun}
                          disabled={busy}
                          onChange={(e) => setLiveRun(e.target.checked)}
                        />
                        <span>Run this demo live on my computer</span>
                      </label>
                    )}
                    <button
                      className="button primary"
                      onClick={runTrace}
                      disabled={busy || !demo}
                    >
                      {busy ? (
                        <LoaderCircle size={17} className="spin" />
                      ) : (
                        <ScanLine size={17} />
                      )}
                      <span>
                        {busy
                          ? "Tracing your clip…"
                          : report
                            ? "Run trace again"
                            : "Find the source"}
                      </span>
                      {!busy && <ArrowRight size={17} />}
                    </button>
                    <button
                      className="upload-button"
                      disabled={busy}
                      onClick={() => input.current?.click()}
                    >
                      <Upload size={15} />
                      Upload your own clip<span>60s max</span>
                    </button>
                    <input
                      ref={input}
                      hidden
                      type="file"
                      accept="video/*,.mkv"
                      onChange={(e) => {
                        chooseFile(e.target.files?.[0]);
                        e.target.value = "";
                      }}
                    />
                  </div>
                  <div className="divider-label">OR TRY ANOTHER EDIT</div>
                  <div className="demo-options">
                    {manifest?.demos.map((d, i) => (
                      <button
                        disabled={busy}
                        key={d.id}
                        className={`demo-option ${!upload && demo?.id === d.id ? "selected" : ""}`}
                        onClick={() => chooseDemo(d)}
                      >
                        <img src={d.thumbnail} alt="" />
                        <div>
                          <strong>{d.title}</strong>
                          <small>
                            {
                              [
                                "Crop + speed change",
                                "Grade + text overlay",
                                "Flip + slow motion",
                                "An honest no-match",
                                "Two sources in one clip",
                              ][i]
                            }
                          </small>
                        </div>
                        {!upload && demo?.id === d.id ? (
                          <span className="selected-check">
                            <Check size={12} />
                          </span>
                        ) : (
                          <ChevronRight size={14} />
                        )}
                      </button>
                    ))}
                  </div>
                  <div className="privacy-note">
                    <ShieldCheck size={14} />
                    <span>
                      {health
                        ? "Video analysis stays on this computer."
                        : "Demo footage is openly licensed and attributed."}
                    </span>
                  </div>
                </section>
                <section
                  className={`results-panel panel ${report ? "has-results" : ""}`}
                  aria-live="polite"
                >
                  <div className="panel-heading">
                    <div>
                      <span className="step-number">02</span>
                      <h2>The source, revealed</h2>
                    </div>
                    {report ? (
                      <span className="result-status">
                        <span />
                        {match ? "Match verified" : "No verified match"}
                      </span>
                    ) : (
                      <span className="micro-label">THE EVIDENCE</span>
                    )}
                  </div>
                  {error && (
                    <div className="error-message" role="alert">
                      <Info size={18} />
                      <p>{error}</p>
                      <button
                        aria-label="Dismiss error"
                        onClick={() => setError("")}
                      >
                        <X size={15} />
                      </button>
                    </div>
                  )}
                  {busy ? (
                    <div className="working-state">
                      <div className="scan-animation">
                        <ScanLine size={45} />
                      </div>
                      <h3>{stage}</h3>
                      <p>
                        {upload || (liveRun && health)
                          ? "Reading actual pixels, retrieving candidates, and checking visual correspondence."
                          : "This is an actual saved pipeline output, not a simulated live inference."}
                      </p>
                      <div className="working-steps">
                        <span>
                          <Film size={15} />
                          Extract frames
                        </span>
                        <ChevronRight size={14} />
                        <span>
                          <Sparkles size={15} />
                          Retrieve
                        </span>
                        <ChevronRight size={14} />
                        <span>
                          <Focus size={15} />
                          Verify
                        </span>
                      </div>
                    </div>
                  ) : !report ? (
                    <div className="empty-state">
                      <div className="source-collage">
                        {manifest?.sources.slice(0, 3).map((s, i) => (
                          <div className={`collage-card card-${i}`} key={s.id}>
                            <img src={s.thumbnail} alt={s.title} />
                            <span>
                              <Film size={12} />
                              {s.title}
                            </span>
                          </div>
                        ))}
                        <div className="collage-focus">
                          <ScanLine size={27} />
                        </div>
                      </div>
                      <div className="empty-copy">
                        <span className="pill neutral">
                          FROM EDIT TO ORIGIN
                        </span>
                        <h2>
                          Different cut.
                          <br />
                          Same story.
                        </h2>
                        <p>
                          A crop, a filter, a faster playback.
                          <br />
                          Traceback looks beneath the edit to find what
                          connects.
                        </p>
                      </div>
                      <div className="empty-pipeline">
                        <div>
                          <span>1</span>
                          <strong>Understand</strong>
                          <small>Multimodal retrieval</small>
                        </div>
                        <i />
                        <div>
                          <span>2</span>
                          <strong>Verify</strong>
                          <small>Visual correspondence</small>
                        </div>
                        <i />
                        <div>
                          <span>3</span>
                          <strong>Trace</strong>
                          <small>Source timestamps</small>
                        </div>
                      </div>
                      <div className="library-summary">
                        <Layers3 size={15} />
                        <span>
                          Searching {manifest?.sources.length || 0} indexed
                          excerpts
                        </span>
                        <button onClick={() => setPage("library")}>
                          View library
                          <ArrowUpRight size={13} />
                        </button>
                      </div>
                    </div>
                  ) : match && evidence ? (
                    <>
                      <div className="match-summary">
                        <div className="match-check">
                          <CheckCheck size={23} />
                        </div>
                        <div>
                          <h3>
                            {match.source.title}
                            <span className="pill green">
                              {match.verdict === "strong"
                                ? "Strong visual evidence"
                                : "Partial visual evidence"}
                            </span>
                          </h3>
                          <p>
                            {match.source.work}
                            <span>·</span>
                            {match.source.creator}
                            <span>·</span>
                            {match.source.license}
                          </p>
                        </div>
                        <button
                          className="icon-button"
                          aria-label="Inspect source video"
                          onClick={() =>
                            openSource(match.source, evidence.sourceTime)
                          }
                        >
                          <ArrowUpRight size={19} />
                        </button>
                      </div>
                      <div className="metrics">
                        <div>
                          <span>Source interval</span>
                          <strong>
                            {shortTime(Math.round(match.alignment.sourceStart))}
                            <ArrowRight size={14} />
                            {shortTime(Math.round(match.alignment.sourceEnd))}
                          </strong>
                          <small>
                            {match.alignment.timingAmbiguous
                              ? "one of multiple possible intervals"
                              : "within the indexed excerpt"}
                          </small>
                        </div>
                        <div>
                          <span>Matched playback change</span>
                          <strong>
                            {match.alignment.speedReliable === false
                              ? "Uncertain"
                              : match.alignment.speed.toFixed(2)}
                            <em>
                              {match.alignment.speedReliable === false
                                ? ""
                                : "×"}
                            </em>
                            {evidence.mirrored && (
                              <span className="mini-tag">flipped</span>
                            )}
                          </strong>
                          <small>
                            {match.alignment.speedRange
                              ? `${match.alignment.speedRange[0].toFixed(2)}–${match.alignment.speedRange[1].toFixed(2)}× consistent range`
                              : "source seconds / clip second"}
                          </small>
                        </div>
                        <div>
                          <span>Verified frames</span>
                          <strong>
                            {match.alignment.support}
                            <em> / {report.query.sampledFrames}</em>
                          </strong>
                          <small>in temporal agreement</small>
                        </div>
                      </div>
                      <div className="comparison-toolbar">
                        <div>
                          <Focus size={15} />
                          <strong>Look at the evidence</strong>
                        </div>
                        <button
                          className={showFeatures ? "toggle active" : "toggle"}
                          aria-pressed={showFeatures}
                          onClick={() => setShowFeatures(!showFeatures)}
                        >
                          <span className="toggle-track">
                            <i />
                          </span>
                          Feature matches
                        </button>
                      </div>
                      <EvidencePair
                        evidence={evidence}
                        base={base}
                        showFeatures={showFeatures}
                      />
                      <div className="evidence-caption">
                        <span>
                          <span className="evidence-dot" />
                          {evidence.inliers} geometrically consistent features
                        </span>
                        <span>
                          Frame pair {activeEvidence + 1} /{" "}
                          {match.evidence.length}
                        </span>
                      </div>
                      <div className="filmstrip">
                        {match.evidence.map((e, i) => (
                          <button
                            key={i}
                            className={
                              i === activeEvidence
                                ? "frame-thumb active"
                                : "frame-thumb"
                            }
                            onClick={() => setActiveEvidence(i)}
                            aria-label={`Inspect frame pair at ${time(e.queryTime)}`}
                            aria-pressed={i === activeEvidence}
                          >
                            <img src={base + e.sourceImage} alt="" />
                            <span>{shortTime(e.queryTime)}</span>
                          </button>
                        ))}
                      </div>
                      <Timeline
                        match={match}
                        duration={report.query.duration}
                      />
                      <div className="evidence-footer">
                        <div>
                          <ShieldCheck size={16} />
                          <p>
                            Shared imagery, backed by inspectable evidence.
                            <br />
                            <span>
                              This does not establish ownership or infringement.
                            </span>
                          </p>
                        </div>
                        <button
                          onClick={exportReport}
                          disabled={exporting}
                          aria-label="Download evidence packet"
                        >
                          <ArrowDownToLine size={18} />
                        </button>
                      </div>
                    </>
                  ) : (
                    <div className="no-match">
                      <Search size={37} />
                      <h3>No source verified.</h3>
                      <p>
                        We couldn’t find enough consistent visual and timestamp
                        evidence in this library. That doesn’t mean the clip is
                        original.
                      </p>
                      <button
                        className="button secondary"
                        onClick={() => setPage("library")}
                      >
                        Explore the source library
                        <ArrowRight size={16} />
                      </button>
                    </div>
                  )}
                </section>
              </div>
              {report && (
                <section className="run-details">
                  <div>
                    <span className="pill neutral">
                      <Clock3 size={12} />
                      {report.recorded ? "RECORDED RUN" : "LIVE LOCAL RUN"}
                    </span>
                    <span>
                      {report.elapsedSeconds.toFixed(1)}s actual processing
                    </span>
                    <span>
                      {report.retrieval.engine === "visual-only"
                        ? "Visual verification"
                        : "Qwen3-VL-Embedding-2B"}
                    </span>
                    <button onClick={() => setPage("method")}>
                      Inspect the method
                      <ArrowUpRight size={13} />
                    </button>
                  </div>
                  {health?.gemini && (
                    <button
                      className="button secondary small"
                      onClick={explain}
                    >
                      <Sparkles size={14} />
                      Explain with Gemini
                    </button>
                  )}
                </section>
              )}
              {explanation && (
                <section className="explanation panel">
                  <h3>
                    <Sparkles size={17} />
                    Grounded explanation
                  </h3>
                  <p>{explanation}</p>
                </section>
              )}
              {report && report.results.length > 1 && (
                <section
                  className="source-map panel"
                  aria-label="Verified source map"
                >
                  <header>
                    <div>
                      <span className="eyebrow">
                        ONE CLIP, MULTIPLE ORIGINS
                      </span>
                      <h2>
                        {report.results.length} sources, mapped to your edit.
                      </h2>
                    </div>
                    <span>Select a source to inspect its evidence</span>
                  </header>
                  <div className="source-map-lanes">
                    {[...report.results]
                      .sort(
                        (a, b) =>
                          a.alignment.queryStart - b.alignment.queryStart,
                      )
                      .map((m) => {
                        const index = report.results.indexOf(m);
                        return (
                          <div className="source-map-row" key={m.source.id}>
                            <button
                              className={activeMatch === index ? "active" : ""}
                              onClick={() => {
                                setActiveMatch(index);
                                setActiveEvidence(0);
                              }}
                              aria-pressed={activeMatch === index}
                            >
                              {m.source.title}
                              <small>
                                {m.alignment.support} verified frames
                              </small>
                            </button>
                            <div className="source-map-track">
                              <button
                                style={{
                                  left: `${(100 * m.alignment.queryStart) / report.query.duration}%`,
                                  width: `${Math.max(3, (100 * (m.alignment.queryEnd - m.alignment.queryStart)) / report.query.duration)}%`,
                                }}
                                className={
                                  activeMatch === index ? "active" : ""
                                }
                                onClick={() => {
                                  setActiveMatch(index);
                                  setActiveEvidence(0);
                                }}
                                aria-label={`Inspect ${m.source.title} from ${time(m.alignment.queryStart)} to ${time(m.alignment.queryEnd)}`}
                              >
                                <span>
                                  {time(m.alignment.queryStart)} —{" "}
                                  {time(m.alignment.queryEnd)}
                                </span>
                              </button>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                  <p>
                    Bars span visually verified query frames. Gaps are not
                    evidence of original content. Sources can overlap.
                  </p>
                </section>
              )}
              <footer className="page-footer">
                <span>
                  <ShieldCheck size={13} />
                  Evidence over assertion.
                </span>
                <span>Made for Gator Hack V · Open source by design</span>
              </footer>
            </>
          )}
          {page === "library" && (
            <Library
              manifest={manifest}
              health={health}
              onInspect={openSource}
              onSources={(sources) =>
                setManifest((m) => (m ? { ...m, sources } : m))
              }
            />
          )}
          {page === "method" && <Method health={health} />}
        </div>
      </main>
      {toast && (
        <div className="toast" role="status">
          <Check size={16} />
          {toast}
        </div>
      )}
      {inspectSource && (
        <div className="modal-backdrop" onClick={closeSource}>
          <section
            ref={modal}
            className="source-modal"
            role="dialog"
            aria-modal="true"
            aria-label={inspectSource.title}
            onClick={(e) => e.stopPropagation()}
          >
            <header>
              <div>
                <span className="eyebrow">INDEXED SOURCE</span>
                <h2>{inspectSource.title}</h2>
              </div>
              <button
                className="icon-button"
                aria-label="Close source preview"
                autoFocus
                onClick={closeSource}
              >
                <X size={21} />
              </button>
            </header>
            <video
              src={inspectSource.url}
              controls
              autoPlay
              muted
              playsInline
              onLoadedMetadata={(e) => {
                e.currentTarget.currentTime = inspectTime;
              }}
            />
            <div className="source-modal-body">
              <p>{inspectSource.description}</p>
              <dl>
                <div>
                  <dt>Original work</dt>
                  <dd>{inspectSource.work}</dd>
                </div>
                <div>
                  <dt>Excerpt begins</dt>
                  <dd>{time(inspectSource.originalOffset)} in original film</dd>
                </div>
                <div>
                  <dt>Attribution</dt>
                  <dd>(CC) Blender Foundation | mango.blender.org</dd>
                </div>
                <div>
                  <dt>License</dt>
                  <dd>
                    {inspectSource.licenseUrl ? (
                      <a
                        href={inspectSource.licenseUrl}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {inspectSource.license}
                        <ExternalLink size={12} />
                      </a>
                    ) : (
                      inspectSource.license
                    )}
                  </dd>
                </div>
              </dl>
              <div className="hash-label">SOURCE SHA-256</div>
              <code>{inspectSource.sha256}</code>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function EvidencePair({
  evidence: e,
  base,
  showFeatures,
}: {
  evidence: Evidence;
  base: string;
  showFeatures: boolean;
}) {
  return (
    <div className="evidence-pair">
      {(["query", "source"] as const).map((side) => (
        <div key={side} className={`evidence-image ${side}`}>
          <div className="image-label">
            <span>{side === "query" ? "YOUR CLIP" : "SOURCE FRAME"}</span>
            <span>{time(side === "query" ? e.queryTime : e.sourceTime)}</span>
          </div>
          <div className="evidence-image-inner">
            <img
              src={base + (side === "query" ? e.queryImage : e.sourceImage)}
              alt={
                side === "query"
                  ? "Edited query frame"
                  : "Matching source frame"
              }
            />
            {showFeatures && (
              <svg
                className="feature-overlay"
                viewBox="0 0 1 1"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                {e.points.map((p, i) => (
                  <g key={i}>
                    <circle
                      cx={p[side][0]}
                      cy={p[side][1]}
                      r=".012"
                      fill="#d4f281"
                      fillOpacity=".16"
                    />
                    <circle
                      cx={p[side][0]}
                      cy={p[side][1]}
                      r=".004"
                      fill="#d4f281"
                    />
                  </g>
                ))}
                {side === "source" && (
                  <polygon
                    points={e.quad.map((p) => p.join(",")).join(" ")}
                    fill="#d4f281"
                    fillOpacity=".06"
                    stroke="#d4f281"
                    strokeWidth=".004"
                    strokeDasharray=".018 .012"
                  />
                )}
              </svg>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function Timeline({ match, duration }: { match: Match; duration: number }) {
  const a = match.alignment;
  return (
    <div className="timeline">
      <div className="timeline-heading">
        <strong>
          <GitBranch size={14} />
          The edit, mapped back
        </strong>
        <span>
          ±{(a.toleranceSeconds ?? 0.65).toFixed(2)}s consensus tolerance
        </span>
      </div>
      <div className="timeline-row">
        <label>Your clip</label>
        <div className="timeline-track query-track">
          <span
            style={{
              left: `${(a.queryStart / duration) * 100}%`,
              width: `${Math.max(2, ((a.queryEnd - a.queryStart) / duration) * 100)}%`,
            }}
          />
          {a.matches.map((m, i) => (
            <i key={i} style={{ left: `${(m.queryTime / duration) * 100}%` }} />
          ))}
        </div>
        <span>{shortTime(duration)}</span>
      </div>
      <div className="timeline-row">
        <label>Source</label>
        <div className="timeline-track source-track">
          <span
            style={{
              left: `${(Math.max(0, a.sourceStart) / match.source.duration) * 100}%`,
              width: `${Math.min(100, ((a.sourceEnd - a.sourceStart) / match.source.duration) * 100)}%`,
            }}
          />
        </div>
        <span>{shortTime(match.source.duration)}</span>
      </div>
      {a.timingAmbiguous && (
        <p className="timing-warning">
          Repeated imagery supports more than one timing explanation. Inspect
          the frame pairs before choosing an interval.
        </p>
      )}
      <p>
        {a.speedReliable === false
          ? "Tentative fit: source time"
          : "Source time"}{" "}
        = {a.speed.toFixed(2)} × clip time + {a.offset.toFixed(2)}s{" "}
        <span>·</span> Median timing residual {a.residual.toFixed(2)}s
      </p>
    </div>
  );
}

function Method({ health }: { health: Health | null }) {
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="tiny-line" />
            NO BLACK-BOX VERDICTS
          </div>
          <h1>Trust the trail.</h1>
          <p>
            A recent retrieval model. Two independent checks. Evidence you can
            reproduce.
          </p>
        </div>
      </section>
      <div className="method-hero">
        <div>
          <span className="pill lime">
            FRESH OFF THE FRONTIER · JANUARY 2026
          </span>
          <h2>
            Meaning finds the candidates.
            <br />
            Geometry earns the match.
          </h2>
          <p>
            Qwen3-VL-Embedding places video frames and language in the same
            vector space. Traceback uses it to rank source candidates, then
            independently tests shared visual structure and consistent time.
          </p>
          <a
            href="https://arxiv.org/abs/2601.04720"
            target="_blank"
            rel="noreferrer"
          >
            Read the model’s research paper
            <ArrowUpRight size={16} />
          </a>
        </div>
        <div className="method-symbol">
          <Layers3 size={80} />
          <span>
            2048-dimensional
            <br />
            multimodal embeddings
          </span>
        </div>
      </div>
      <div className="method-grid">
        {[
          {
            n: "01",
            icon: Sparkles,
            title: "Retrieve by meaning",
            text: "The January 2026 Qwen3-VL-Embedding-2B model embeds actual frame pixels. Cosine similarity ranks potential sources. With this small demo library, all candidates are retained to avoid hiding a true match.",
          },
          {
            n: "02",
            icon: Focus,
            title: "Verify the pixels",
            text: "ORB features find local visual correspondences. A ratio test and RANSAC homography reject inconsistent matches. The green points show actual inlier features; the outline maps the query’s field of view.",
          },
          {
            n: "03",
            icon: GitBranch,
            title: "Reconstruct the edit",
            text: "Timestamp consensus estimates playback speed and source offset. Multiple matching frames must agree on one temporal mapping. One similar frame is not enough to produce a source match.",
          },
        ].map((s) => (
          <article className="method-card" key={s.n}>
            <span>{s.n}</span>
            <s.icon size={26} />
            <h3>{s.title}</h3>
            <p>{s.text}</p>
          </article>
        ))}
      </div>
      <Evaluation />
      <Diagnostics />
      <div className="method-bottom">
        <section className="panel">
          <h3>
            <ShieldCheck size={19} />
            What this can establish
          </h3>
          <ul>
            <li>Shared imagery with a source in the indexed library.</li>
            <li>Approximate source timestamps and playback changes.</li>
            <li>Inspectable feature correspondences and file hashes.</li>
          </ul>
          <h3 className="limits-heading">
            <Info size={19} />
            What it cannot establish
          </h3>
          <ul>
            <li>
              Who owns the rights, whether reuse is lawful, or which copy was
              published first.
            </li>
            <li>
              That an unmatched clip is original or that a matched clip is
              deceptive.
            </li>
            <li>
              Internet-wide coverage. This demonstration searches four known
              excerpts.
            </li>
          </ul>
        </section>
        <section className="panel integration-panel">
          <h3>
            <Layers3 size={19} />
            Run transparency
          </h3>
          <div>
            <span>Local retrieval engine</span>
            <strong className={health ? "ready" : ""}>
              {health ? "Connected" : "Hosted recorded demo"}
            </strong>
          </div>
          <div>
            <span>Gemini explanation</span>
            <strong className={health?.gemini ? "ready" : ""}>
              {health?.gemini ? "Configured" : "API key required"}
            </strong>
          </div>
          <div>
            <span>Twinly integration</span>
            <strong className={health?.twinly ? "ready" : ""}>
              {health?.twinly ? "Configured" : "API key required"}
            </strong>
          </div>
          <p>
            Recorded demos are generated by the real local pipeline. New uploads
            run on your local server. Sponsor features are never represented as
            live calls when credentials are missing.
          </p>
          <a href={asset("/manifest.json")} target="_blank" rel="noreferrer">
            Inspect the media manifest
            <ArrowUpRight size={14} />
          </a>
        </section>
      </div>
    </>
  );
}

export default App;
