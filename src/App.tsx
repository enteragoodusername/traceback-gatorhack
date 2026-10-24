import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  Check,
  ChevronDown,
  Clock3,
  Copy,
  Film,
  Globe2,
  Info,
  LoaderCircle,
  Play,
  ScanLine,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import {
  embedUrl,
  timestamp,
  watchUrl,
  type SavedVideo,
  type VideoCandidate,
  type VideoSearch,
} from "./internet";

type Connection = "checking" | "ready" | "offline";
const LAST_SEARCH = "traceback:internet:last-search";
const SAVED_VIDEOS = "traceback:internet:saved-videos";
const STAGES = ["frames", "describe", "search", "thumbnails", "rank"];
const STAGE_NAMES = [
  "Read clip",
  "Describe scenes",
  "Search the web",
  "Get previews",
  "Compare visuals",
];
function readSaved(): SavedVideo[] {
  try {
    const value = JSON.parse(localStorage.getItem(SAVED_VIDEOS) || "[]");
    return Array.isArray(value)
      ? value
          .filter(
            (v) =>
              v &&
              typeof v.id === "string" &&
              typeof v.title === "string" &&
              watchUrl(v.url),
          )
          .slice(0, 100)
      : [];
  } catch {
    return [];
  }
}

export default function App() {
  const [connection, setConnection] = useState<Connection>("checking");
  const [view, setView] = useState<"search" | "saved">("search");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState("frames");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [queryUrl, setQueryUrl] = useState("");
  const [jobId, setJobId] = useState("");
  const [result, setResult] = useState<VideoSearch | null>(null);
  const [recent, setRecent] = useState("");
  const [filter, setFilter] = useState("All");
  const [refine, setRefine] = useState("");
  const [saved, setSaved] = useState<SavedVideo[]>(readSaved);
  const [compare, setCompare] = useState<VideoCandidate | null>(null);
  const [toast, setToast] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const requestId = useRef(0);
  const inFlight = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const modal = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  async function checkConnection() {
    setConnection("checking");
    try {
      const r = await fetch("/api/health", {
        signal: AbortSignal.timeout(3000),
      });
      const health = r.ok ? await r.json() : null;
      setConnection(health?.mode === "internet-search" ? "ready" : "offline");
    } catch {
      setConnection("offline");
    }
  }
  useEffect(() => {
    void checkConnection();
    try {
      const id = localStorage.getItem(LAST_SEARCH);
      if (id && /^[a-f0-9]{32}$/.test(id)) setRecent(id);
    } catch {
      /* Browser storage is optional. */
    }
    return () => {
      requestId.current++;
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setQueryUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    try {
      localStorage.setItem(SAVED_VIDEOS, JSON.stringify(saved));
    } catch {
      /* Saving links never blocks search. */
    }
  }, [saved]);
  useEffect(() => {
    if (!compare) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    modal.current?.querySelector<HTMLElement>("button")?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeCompare();
      if (e.key === "Tab") {
        const controls = modal.current?.querySelectorAll<HTMLElement>(
          "button,a[href],video[controls],iframe",
        );
        if (!controls?.length) return;
        const first = controls[0],
          last = controls[controls.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
        if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKey);
    };
  }, [compare]);

  function closeCompare() {
    setCompare(null);
    returnFocus.current?.focus();
  }
  function openCompare(candidate: VideoCandidate) {
    returnFocus.current = document.activeElement as HTMLElement;
    setCompare(candidate);
  }
  function begin() {
    if (inFlight.current) return null;
    inFlight.current = true;
    const id = ++requestId.current;
    controller.current?.abort();
    controller.current = new AbortController();
    setBusy(true);
    setError("");
    setResult(null);
    setCompare(null);
    setFilter("All");
    setView("search");
    setStage("frames");
    setMessage("Uploading your video to the local engine");
    return id;
  }
  async function poll(id: number, job: string) {
    setJobId(job);
    setRecent(job);
    try {
      localStorage.setItem(LAST_SEARCH, job);
    } catch {
      /* Optional recovery. */
    }
    for (;;) {
      if (id !== requestId.current) return;
      const response = await fetch(`/api/jobs/${job}`, {
        signal: AbortSignal.any([
          controller.current!.signal,
          AbortSignal.timeout(15000),
        ]),
      });
      if (!response.ok)
        throw Error(
          response.status === 404
            ? "This search is no longer available. Choose your video to start a fresh search."
            : "Could not read search progress. Reopen the latest search to reconnect.",
        );
      const data = await response.json();
      if (id !== requestId.current) return;
      setStage(data.stage || "frames");
      setMessage(data.message || "Searching…");
      if (data.status === "failed")
        throw Error(data.error || "Search failed. Try again.");
      if (data.status === "complete") {
        if (!data.result || data.result.schemaVersion !== "internet-1")
          throw Error(
            "This is not an internet video search. Choose a video to start a fresh search.",
          );
        setResult(data.result);
        setRefine(data.result.queries[0] || "");
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
  function finish(id: number, problem?: unknown) {
    if (id !== requestId.current) return;
    if (problem)
      setError(
        problem instanceof Error ? problem.message : "Search could not finish.",
      );
    inFlight.current = false;
    setBusy(false);
  }
  async function chooseFile(next?: File) {
    if (!next || inFlight.current) return;
    if (connection !== "ready") {
      setError(
        "Open the local app to analyze a video. The website has no cloud video engine or prerecorded answers.",
      );
      return;
    }
    if (next.size > 100 * 1024 * 1024) {
      setError("Choose a video smaller than 100 MB.");
      return;
    }
    if (!/\.(mp4|mov|webm|mkv|m4v)$/i.test(next.name)) {
      setError("Choose an MP4, MOV, WebM, MKV or M4V video.");
      return;
    }
    const id = begin();
    if (id === null) return;
    setFile(next);
    setJobId("");
    try {
      const form = new FormData();
      form.append("file", next);
      const response = await fetch("/api/search-video", {
        method: "POST",
        body: form,
        signal: AbortSignal.any([
          controller.current!.signal,
          AbortSignal.timeout(120000),
        ]),
      });
      const data = await response.json();
      if (!response.ok)
        throw Error(data.detail || "Could not start the video search.");
      if (id !== requestId.current) return;
      await poll(id, data.id);
      finish(id);
    } catch (problem) {
      finish(id, problem);
    }
  }
  async function reopen() {
    if (!recent || connection !== "ready") return;
    const id = begin();
    if (id === null) return;
    setFile(null);
    setQueryUrl(`/api/query/${recent}`);
    try {
      await poll(id, recent);
      finish(id);
    } catch (problem) {
      finish(id, problem);
    }
  }
  async function refineSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!jobId || refine.trim().length < 2) return;
    const id = begin();
    if (id === null) return;
    try {
      const response = await fetch(`/api/refine/${jobId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: refine.trim() }),
        signal: controller.current!.signal,
      });
      const data = await response.json();
      if (!response.ok)
        throw Error(data.detail || "Could not refine this search.");
      if (id !== requestId.current) return;
      await poll(id, data.id);
      finish(id);
    } catch (problem) {
      finish(id, problem);
    }
  }
  function toggleSaved(candidate: VideoCandidate, imageUrl?: string) {
    setSaved((previous) =>
      previous.some((v) => v.id === candidate.id)
        ? previous.filter((v) => v.id !== candidate.id)
        : [{ ...candidate, imageUrl }, ...previous].slice(0, 100),
    );
  }
  async function copyLink(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      setToast("Video link copied");
    } catch {
      setToast(
        "Use the video title link to copy its address from your browser.",
      );
    }
  }
  function exportSaved() {
    const text = saved
      .map(
        (v) =>
          `${v.title}\n${v.creator ? v.creator + " · " : ""}${v.provider}\n${v.url}`,
      )
      .join("\n\n");
    const url = URL.createObjectURL(
      new Blob(
        [
          `Traceback · saved video links\n\n${text}\n\nThese are search candidates, not verified sources.\n`,
        ],
        { type: "text/plain" },
      ),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "traceback-video-links.txt";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const assetBase = `/api/search-assets/${jobId}/`;
  const visible = (result?.results || []).filter(
    (v) => filter === "All" || v.provider === filter,
  );
  const name = file?.name || result?.query.filename || "Your clip";
  const providers = Array.from(
    new Set(result?.results.map((v) => v.provider) || []),
  );
  const activeStage = STAGES.indexOf(stage);

  function card(
    candidate: VideoCandidate,
    imageUrl?: string,
    savedView = false,
  ) {
    const isSaved = saved.some((v) => v.id === candidate.id);
    return (
      <article className="video-card" key={candidate.id}>
        <a
          className="candidate-image"
          href={watchUrl(candidate.url)}
          target="_blank"
          rel="noreferrer"
          aria-label={`Watch ${candidate.title}`}
        >
          {imageUrl ? (
            <img
              loading="lazy"
              src={imageUrl}
              alt=""
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          ) : (
            <Film size={35} />
          )}
          <span className="watch-overlay">
            <Play size={23} fill="currentColor" />
          </span>
          {candidate.duration && (
            <span className="duration">{candidate.duration}</span>
          )}
        </a>
        <div className="candidate-copy">
          <div className="candidate-meta">
            <span>{candidate.provider}</span>
            <span>
              {candidate.similarity !== undefined
                ? "Visually ranked"
                : "Search result"}
            </span>
          </div>
          <h3>
            <a href={watchUrl(candidate.url)} target="_blank" rel="noreferrer">
              {candidate.title}
            </a>
          </h3>
          <p>{candidate.creator || "Creator not listed"}</p>
          <div className="candidate-actions">
            {!savedView && (
              <button onClick={() => openCompare(candidate)}>
                <SlidersHorizontal size={14} /> Compare
              </button>
            )}
            <button
              aria-label={`${isSaved ? "Unsave" : "Save"} ${candidate.title}`}
              aria-pressed={isSaved}
              onClick={() => toggleSaved(candidate, imageUrl)}
            >
              <Bookmark size={15} fill={isSaved ? "currentColor" : "none"} />
              {isSaved ? "Saved" : "Save"}
            </button>
            <button
              className="copy-action"
              aria-label={`Copy link to ${candidate.title}`}
              onClick={() => void copyLink(candidate.url)}
            >
              <Copy size={15} />
            </button>
          </div>
        </div>
      </article>
    );
  }

  return (
    <div className="internet-app">
      <a className="skip-link" href="#main-content">
        Skip to video search
      </a>
      <header className="app-header">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView("search");
          }}
          aria-label="Traceback home"
        >
          <span className="brand-icon">
            <ScanLine size={23} />
          </span>
          traceback<span className="brand-dot">.</span>
        </a>
        <nav aria-label="Main navigation">
          <button
            className={view === "search" ? "active" : ""}
            aria-current={view === "search" ? "page" : undefined}
            onClick={() => setView("search")}
          >
            <Search size={16} /> Video search
          </button>
          <button
            className={view === "saved" ? "active" : ""}
            aria-current={view === "saved" ? "page" : undefined}
            onClick={() => setView("saved")}
          >
            <Bookmark size={16} /> Saved videos <span>{saved.length}</span>
          </button>
        </nav>
        <span className={`connection ${connection}`}>
          <i />
          {connection === "ready"
            ? "Live engine connected"
            : connection === "checking"
              ? "Connecting…"
              : "Local engine needed"}
        </span>
      </header>
      <main id="main-content" tabIndex={-1}>
        {view === "search" ? (
          <>
            <section className={`search-heading ${queryUrl ? "compact" : ""}`}>
              <div className="eyebrow">
                <Globe2 size={14} /> A CLIP IS ALL YOU NEED
              </div>
              <h1>
                Find videos like <em>this one.</em>
              </h1>
              <p>
                Drop a clip. Search the internet. Discover footage worth
                watching.
              </p>
            </section>
            {connection === "offline" && (
              <section className="connection-panel">
                <div>
                  <Globe2 size={22} />
                  <h2>Connect your local search engine</h2>
                  <p>
                    Video understanding runs on your computer. Scene
                    descriptions are sent to YouTube and Internet Archive; your
                    video stays local.
                  </p>
                  <details>
                    <summary>
                      Start the app <ChevronDown size={14} />
                    </summary>
                    <p>
                      In the project folder, run <code>./setup.sh</code> once,
                      then <code>./start.sh</code>. The first search downloads
                      the caption and ranking models if needed.
                    </p>
                  </details>
                </div>
                <div className="connection-actions">
                  <a
                    className="button primary"
                    href="http://127.0.0.1:8000"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open local app <ArrowUpRight size={16} />
                  </a>
                  <button
                    className="button secondary"
                    onClick={() => void checkConnection()}
                  >
                    Check connection
                  </button>
                </div>
              </section>
            )}
            <section
              className={`clip-input ${dragging ? "dragging" : ""} ${queryUrl ? "compact" : ""}`}
              aria-label="Submit a video"
              onDragOver={(e) => {
                e.preventDefault();
                if (!busy) setDragging(true);
              }}
              onDragLeave={(e) => {
                if (!e.currentTarget.contains(e.relatedTarget as Node))
                  setDragging(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                void chooseFile(e.dataTransfer.files[0]);
              }}
            >
              <div className="upload-mark">
                <Upload size={queryUrl ? 22 : 29} />
              </div>
              <div className="drop-copy">
                <h2>
                  {busy
                    ? "Searching with your clip…"
                    : queryUrl
                      ? "Try another video"
                      : "Drop your video here"}
                </h2>
                <p>
                  {busy
                    ? "You can leave this tab open while the engine works."
                    : "Choose one file. The search starts automatically."}
                </p>
                <small>MP4, MOV, WebM, MKV · 2–60 seconds · up to 100 MB</small>
              </div>
              <button
                className="button primary"
                onClick={() => input.current?.click()}
                disabled={busy || connection !== "ready"}
              >
                {busy ? (
                  <LoaderCircle size={17} className="spin" />
                ) : (
                  <Film size={17} />
                )}
                {busy ? "Searching…" : "Choose a video"}
              </button>
              <input
                ref={input}
                type="file"
                className="visually-hidden"
                aria-label="Choose a video file"
                disabled={busy || connection !== "ready"}
                accept="video/*,.mkv,.m4v"
                onChange={(e) => {
                  void chooseFile(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
            </section>
            {!queryUrl && (
              <p className="privacy-note">
                <ShieldCheck size={14} /> Your file stays on this computer. Only
                generated search text goes online.
              </p>
            )}
            {recent && !busy && !result && connection === "ready" && (
              <button className="reopen-button" onClick={() => void reopen()}>
                <Clock3 size={15} /> Reopen latest search{" "}
                <ArrowRight size={14} />
              </button>
            )}
            {error && (
              <div className="error-message" role="alert">
                <Info size={19} />
                <p>{error}</p>
                {file && connection === "ready" && (
                  <button onClick={() => void chooseFile(file)}>Retry</button>
                )}
                <button aria-label="Dismiss error" onClick={() => setError("")}>
                  <X size={17} />
                </button>
              </div>
            )}
            {queryUrl && (
              <div className="search-workspace">
                <aside className="query-panel">
                  <div className="section-label">YOUR CLIP</div>
                  <video
                    ref={video}
                    key={queryUrl}
                    src={queryUrl}
                    controls
                    playsInline
                    preload="metadata"
                    aria-label="Your uploaded clip"
                  />
                  <h2>{name}</h2>
                  {result && (
                    <p>
                      {result.query.duration.toFixed(1)} seconds · searched{" "}
                      {new Date(result.searchedAt).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  )}
                  {result && (
                    <>
                      <div className="query-frames">
                        {result.frames.map((frame, i) => (
                          <button
                            key={frame.image}
                            aria-label={`Jump to frame at ${timestamp(frame.time)}`}
                            onClick={() => {
                              if (video.current)
                                video.current.currentTime = frame.time;
                            }}
                          >
                            <img
                              src={assetBase + frame.image}
                              alt={`Sampled scene ${i + 1}`}
                            />
                            <span>{timestamp(frame.time)}</span>
                          </button>
                        ))}
                      </div>
                      <details className="search-refinement">
                        <summary>
                          <SlidersHorizontal size={14} /> Refine the description{" "}
                          <ChevronDown size={14} />
                        </summary>
                        <p>
                          Scene descriptions can miss details. Adjust the words
                          to search again with the same clip.
                        </p>
                        <form onSubmit={refineSearch}>
                          <label htmlFor="refine-query">
                            Search description
                          </label>
                          <textarea
                            id="refine-query"
                            value={refine}
                            maxLength={200}
                            onChange={(e) => setRefine(e.target.value)}
                          />
                          <button
                            className="button secondary"
                            disabled={busy || refine.trim().length < 2}
                          >
                            Search again <ArrowRight size={14} />
                          </button>
                        </form>
                      </details>
                    </>
                  )}
                  <div className="query-note">
                    <ShieldCheck size={16} />
                    <p>
                      Similar imagery is a lead. It doesn’t prove an original
                      source or permission to reuse.
                    </p>
                  </div>
                </aside>
                <section
                  className="search-output"
                  aria-label="Internet video results"
                >
                  {busy ? (
                    <div className="working-state" role="status">
                      <div className="scan-orbit">
                        <ScanLine size={35} />
                      </div>
                      <span className="eyebrow">LIVE INTERNET SEARCH</span>
                      <h2>{message}</h2>
                      <p>
                        Local AI work can take a few minutes on a CPU. The first
                        run also downloads any missing models.
                      </p>
                      <ol className="working-steps">
                        {STAGE_NAMES.map((title, i) => (
                          <li
                            key={title}
                            className={
                              i === activeStage
                                ? "current"
                                : i < activeStage
                                  ? "complete"
                                  : ""
                            }
                          >
                            <span>
                              {i < activeStage ? <Check size={13} /> : i + 1}
                            </span>
                            {title}
                          </li>
                        ))}
                      </ol>
                    </div>
                  ) : result ? (
                    <>
                      <div className="results-heading">
                        <div>
                          <div className="eyebrow">
                            <span className="live-dot" /> SEARCHED LIVE
                          </div>
                          <h2>
                            {result.results.length
                              ? "Similar videos to explore"
                              : "No video candidates found"}
                          </h2>
                        </div>
                        <span>{result.results.length} results</span>
                      </div>
                      <p className="search-terms">
                        Searched for{" "}
                        {result.queries.map((q) => `“${q}”`).join(" and ")}.
                      </p>
                      {result.warnings.map((w) => (
                        <p className="search-warning" key={w}>
                          <Info size={15} />
                          {w}
                        </p>
                      ))}
                      {result.results.length ? (
                        <>
                          <div className="result-controls">
                            <div
                              role="group"
                              aria-label="Filter by video provider"
                            >
                              {["All", ...providers].map((p) => (
                                <button
                                  key={p}
                                  aria-pressed={filter === p}
                                  className={filter === p ? "active" : ""}
                                  onClick={() => setFilter(p)}
                                >
                                  {p}
                                </button>
                              ))}
                            </div>
                            <span>
                              <Sparkles size={13} /> Thumbnail similarity
                            </span>
                          </div>
                          <div className="results-grid">
                            {visible.map((c) =>
                              card(
                                c,
                                c.thumbnail
                                  ? assetBase + c.thumbnail
                                  : undefined,
                              ),
                            )}
                          </div>
                        </>
                      ) : (
                        <div className="no-results">
                          <Search size={32} />
                          <p>
                            Try a more specific description or a clip with a
                            clearer subject. Unavailable services are listed
                            below.
                          </p>
                          <a
                            className="button secondary"
                            href={`https://www.youtube.com/results?search_query=${encodeURIComponent(result.queries[0] || "")}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Continue on YouTube <ArrowUpRight size={15} />
                          </a>
                        </div>
                      )}
                      <details className="search-transparency">
                        <summary>
                          How these results were found <ChevronDown size={14} />
                        </summary>
                        <p>{result.limitation}</p>
                        <ul>
                          {result.providers.map((p, i) => (
                            <li key={i}>
                              {p.provider}:{" "}
                              {p.status === "ok"
                                ? `${p.count} candidates returned`
                                : "unavailable"}{" "}
                              for “{p.query}”
                            </li>
                          ))}
                        </ul>
                        <p>
                          Descriptions: BLIP · visual ranking:
                          Qwen3-VL-Embedding-2B ·{" "}
                          {result.elapsedSeconds.toFixed(1)}s processing. A
                          thumbnail score is not a probability of a match.
                        </p>
                      </details>
                    </>
                  ) : (
                    <div className="no-results">
                      <Search size={30} />
                      <h2>Your search will appear here</h2>
                      <p>
                        Retry the upload or reopen the latest search if the
                        connection was interrupted.
                      </p>
                    </div>
                  )}
                </section>
              </div>
            )}
            {!queryUrl && (
              <div className="tool-intro">
                <div>
                  <span>01</span>
                  <Film size={21} />
                  <h3>Show, don’t describe</h3>
                  <p>
                    Start with the clip on your phone or computer. No keywords
                    required.
                  </p>
                </div>
                <div>
                  <span>02</span>
                  <Globe2 size={21} />
                  <h3>Search beyond a library</h3>
                  <p>
                    Discover live video candidates on YouTube and Internet
                    Archive.
                  </p>
                </div>
                <div>
                  <span>03</span>
                  <Bookmark size={21} />
                  <h3>Find your next reference</h3>
                  <p>
                    Compare previews, watch the videos, and save a shortlist of
                    links.
                  </p>
                </div>
              </div>
            )}
          </>
        ) : (
          <section className="saved-page">
            <div className="results-heading">
              <div>
                <div className="eyebrow">YOUR SHORTLIST</div>
                <h1>Worth coming back to.</h1>
                <p>Video links saved in this browser.</p>
              </div>
              <button
                className="button secondary"
                disabled={!saved.length}
                onClick={exportSaved}
              >
                <ArrowDownToLine size={16} /> Export links
              </button>
            </div>
            {saved.length ? (
              <div className="results-grid saved-grid">
                {saved.map((c) => card(c, c.imageUrl, true))}
              </div>
            ) : (
              <div className="saved-empty">
                <Bookmark size={36} />
                <h2>Your next reference starts with a clip.</h2>
                <p>
                  Save videos from your search results to collect them here.
                </p>
                <button
                  className="button primary"
                  onClick={() => setView("search")}
                >
                  Find similar videos <ArrowRight size={16} />
                </button>
              </div>
            )}
          </section>
        )}
      </main>
      <footer className="app-footer">
        <span>
          <ScanLine size={14} /> Traceback · From a clip to a discovery.
        </span>
        <a
          href="https://github.com/enteragoodusername/traceback-gatorhack"
          target="_blank"
          rel="noreferrer"
        >
          Open source <ArrowUpRight size={13} />
        </a>
      </footer>
      {toast && (
        <div className="toast" role="status">
          <Check size={16} />
          {toast}
        </div>
      )}
      {compare && (
        <div className="modal-backdrop" onClick={closeCompare}>
          <div
            className="compare-modal"
            ref={modal}
            role="dialog"
            aria-modal="true"
            aria-label="Compare video candidate"
            onClick={(e) => e.stopPropagation()}
          >
            <header role="presentation">
              <div>
                <span className="eyebrow">SIDE BY SIDE</span>
                <h2>Does it look like your clip?</h2>
              </div>
              <button
                className="icon-button"
                aria-label="Close comparison"
                onClick={closeCompare}
              >
                <X size={22} />
              </button>
            </header>
            <div className="compare-grid">
              <section>
                <h3>Your clip</h3>
                <video
                  src={queryUrl}
                  controls
                  playsInline
                  onLoadedMetadata={(e) => {
                    const frame = result?.frames[compare.matchedFrame ?? 0];
                    if (frame) e.currentTarget.currentTime = frame.time;
                  }}
                />
              </section>
              <section>
                <h3>{compare.title}</h3>
                {embedUrl(compare.url) && (
                  <iframe
                    src={embedUrl(compare.url)}
                    title={`Watch ${compare.title}`}
                    allow="encrypted-media; fullscreen; picture-in-picture"
                    referrerPolicy="strict-origin-when-cross-origin"
                    allowFullScreen
                  />
                )}
              </section>
            </div>
            <footer role="presentation">
              <p>
                {compare.similarity === undefined
                  ? "This is a live search candidate. Its thumbnail could not be visually ranked."
                  : `Thumbnail cosine similarity: ${compare.similarity.toFixed(3)}. This compares a preview image, not the complete video.`}
              </p>
              <a
                className="button primary"
                href={watchUrl(compare.url)}
                target="_blank"
                rel="noreferrer"
              >
                Watch on {compare.provider} <ArrowUpRight size={15} />
              </a>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}
