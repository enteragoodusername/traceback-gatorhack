import { useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  Info,
  LoaderCircle,
  Maximize2,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import type { Manifest, Source } from "./types";
import { asset } from "./paths";

type SemanticHit = { sourceId: string; time: number; similarity: number };
type SavedSearch = { query: string; results: SemanticHit[] };
const shortTime = (n: number) =>
  `${Math.floor(n / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(n % 60)
    .toString()
    .padStart(2, "0")}`;

export default function Library({
  manifest,
  health,
  onInspect,
  onSources,
}: {
  manifest: Manifest | null;
  health: { semantic: boolean } | null;
  onInspect: (s: Source, start?: number) => void;
  onSources: (sources: Source[]) => void;
}) {
  const [filter, setFilter] = useState("");
  const [query, setQuery] = useState("");
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [hits, setHits] = useState<SemanticHit[] | null>(null);
  const [recorded, setRecorded] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [title, setTitle] = useState("");
  const [creator, setCreator] = useState("");
  const [license, setLicense] = useState("Rights unverified");
  const [file, setFile] = useState<File | null>(null);
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    fetch(asset("/semantic-searches.json"))
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.searches) setSearches(data.searches);
      })
      .catch(() => {});
  }, []);
  async function search(text = query) {
    if (text.trim().length < 2) return;
    setQuery(text);
    setError("");
    setSearching(true);
    try {
      const saved = searches.find((s) => s.query === text);
      if (!health?.semantic) {
        if (!saved)
          throw Error(
            "Free-text semantic search runs on the local engine. Try a recorded query below, or start the project locally.",
          );
        setHits(saved.results);
        setRecorded(true);
      } else {
        const response = await fetch("/api/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: text }),
        });
        const data = await response.json();
        if (!response.ok)
          throw Error(data.detail || "Search could not be completed.");
        setHits(data.results);
        setRecorded(false);
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Search could not be completed.",
      );
    } finally {
      setSearching(false);
    }
  }
  async function addSource(event: React.FormEvent) {
    event.preventDefault();
    if (!file || !title.trim()) return;
    setError("");
    setAdding(true);
    setMessage("Preparing your source…");
    try {
      if (file.size > 100 * 1024 * 1024)
        throw Error("Use a source smaller than 100 MB.");
      const form = new FormData();
      form.append("file", file);
      form.append("title", title);
      form.append("creator", creator || "User provided");
      form.append("license", license);
      const response = await fetch("/api/sources", {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      if (!response.ok)
        throw Error(data.detail || "Could not add this source.");
      for (;;) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        const poll = await fetch(`/api/jobs/${data.id}`);
        if (!poll.ok) throw Error("Could not read indexing status.");
        const job = await poll.json();
        setMessage(job.message || "Computing multimodal embeddings…");
        if (job.status === "failed")
          throw Error(job.error || "Indexing failed.");
        if (job.status === "complete") {
          const library = await fetch("/api/library");
          if (!library.ok)
            throw Error(
              "Source was indexed, but the library could not refresh.",
            );
          const updated = await library.json();
          onSources(updated.sources);
          setMessage("Your source is indexed and ready to trace.");
          setFile(null);
          setTitle("");
          setShowAdd(false);
          break;
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add this source.");
      setMessage("");
    } finally {
      setAdding(false);
    }
  }
  const visible =
    manifest?.sources.filter((s) =>
      `${s.title} ${s.description} ${s.creator}`
        .toLowerCase()
        .includes(filter.toLowerCase()),
    ) || [];
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="tiny-line" />
            KNOW WHAT YOU’RE SEARCHING
          </div>
          <h1>A library with provenance.</h1>
          <p>
            Every indexed source has an origin, a license, and a fingerprint.
          </p>
        </div>
        {health ? (
          <button
            className="button secondary"
            onClick={() => setShowAdd(!showAdd)}
            disabled={adding}
          >
            <Plus size={16} />
            Add your source
          </button>
        ) : (
          <span className="pill green">
            {manifest?.sources.length || 0} indexed excerpts
          </span>
        )}
      </section>
      {showAdd && (
        <form className="add-source panel" onSubmit={addSource}>
          <header>
            <h3>
              <Upload size={17} />
              Index a source you have permission to use
            </h3>
            <button
              type="button"
              aria-label="Close source form"
              disabled={adding}
              onClick={() => setShowAdd(false)}
            >
              <X size={16} />
            </button>
          </header>
          <div className="source-form-grid">
            <label>
              Source title
              <input
                required
                maxLength={100}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="A recognizable name for your footage"
                disabled={adding}
              />
            </label>
            <label>
              Creator / attribution
              <input
                maxLength={100}
                value={creator}
                onChange={(e) => setCreator(e.target.value)}
                placeholder="As provided by the rights holder"
                disabled={adding}
              />
            </label>
            <label>
              Rights label
              <select
                value={license}
                onChange={(e) => setLicense(e.target.value)}
                disabled={adding}
              >
                <option>Rights unverified</option>
                <option>All rights reserved</option>
                <option>CC BY 3.0</option>
                <option>CC BY 4.0</option>
                <option>CC0</option>
              </select>
            </label>
            <label>
              Source video · 2–60s, up to 100 MB
              <input
                type="file"
                required
                accept="video/*,.mkv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                disabled={adding}
              />
            </label>
          </div>
          <footer>
            <p>
              Frames and embeddings stay on this computer. Rights metadata is
              user supplied.
            </p>
            <button
              className="button primary"
              type="submit"
              disabled={adding || !file}
            >
              {adding ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Plus size={16} />
              )}
              Index source
            </button>
          </footer>
        </form>
      )}
      {error && (
        <div className="error-message" role="alert">
          <Info size={17} />
          <p>{error}</p>
          <button
            aria-label="Dismiss library error"
            onClick={() => setError("")}
          >
            <X size={15} />
          </button>
        </div>
      )}
      {message && (
        <div className="library-message" role="status">
          {adding ? (
            <LoaderCircle size={15} className="spin" />
          ) : (
            <Check size={15} />
          )}{" "}
          {message}
        </div>
      )}
      <section className="semantic-search panel">
        <div className="semantic-heading">
          <span>
            <Sparkles size={17} />
            Find a moment by meaning
          </span>
          <span className="pill neutral">QWEN3-VL-EMBEDDING · JAN 2026</span>
        </div>
        <p>
          Describe what you remember. The model searches frame pixels, not
          filenames or scene labels.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void search();
          }}
        >
          <Search size={18} />
          <input
            aria-label="Describe a visual moment"
            placeholder="Two people standing beside a canal…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={500}
          />
          <button
            className="button primary"
            disabled={searching || query.trim().length < 2}
          >
            {searching ? (
              <LoaderCircle className="spin" size={15} />
            ) : (
              <ArrowRight size={15} />
            )}
            <span>Search</span>
          </button>
        </form>
        <div className="search-suggestions">
          {searches.map((s) => (
            <button
              key={s.query}
              disabled={searching}
              onClick={() => void search(s.query)}
            >
              {s.query}
              <ArrowUpRight size={11} />
            </button>
          ))}
        </div>
        {hits && (
          <div className="semantic-results">
            <div className="semantic-result-label">
              <span>
                {recorded
                  ? "Recorded text-to-frame retrieval"
                  : "Live text-to-frame retrieval"}
              </span>
              <span>Similarity is not proof of reuse</span>
              <button
                onClick={() => setHits(null)}
                aria-label="Clear semantic results"
              >
                <X size={14} />
              </button>
            </div>
            <div className="semantic-hits">
              {hits.slice(0, 4).map((hit, i) => {
                const source = manifest?.sources.find(
                  (s) => s.id === hit.sourceId,
                );
                return source ? (
                  <button
                    key={`${hit.sourceId}-${hit.time}-${i}`}
                    onClick={() => onInspect(source, hit.time)}
                  >
                    <div>
                      <img
                        src={
                          recorded
                            ? asset(
                                `/semantic-frames/${source.id}-${hit.time}.jpg`,
                              )
                            : `/api/frames/${source.id}/${hit.time}`
                        }
                        onError={(e) => {
                          e.currentTarget.onerror = null;
                          e.currentTarget.style.visibility = "hidden";
                        }}
                        alt={`${source.title} at ${shortTime(hit.time)}`}
                      />
                      <span>{shortTime(hit.time)}</span>
                    </div>
                    <strong>{source.title}</strong>
                    <small>Cosine similarity {hit.similarity.toFixed(3)}</small>
                  </button>
                ) : null;
              })}
            </div>
          </div>
        )}
      </section>
      <div className="library-section-head">
        <h2>
          Indexed sources <span>{manifest?.sources.length || 0}</span>
        </h2>
        <div className="library-search">
          <Search size={16} />
          <input
            aria-label="Filter source library"
            placeholder="Filter sources…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
      </div>
      <div className="library-grid">
        {visible.map((s) => (
          <button
            key={s.id}
            className="source-card"
            onClick={() => onInspect(s)}
          >
            <div className="source-card-image">
              <img src={s.thumbnail} alt={s.title} />
              <span>{shortTime(s.duration)}</span>
              <i>
                <Maximize2 size={18} />
              </i>
            </div>
            <div className="source-card-body">
              <span className="micro-label">{s.category}</span>
              <h2>
                {s.title}
                <ArrowUpRight size={18} />
              </h2>
              <p>{s.description}</p>
              <div>
                <span>
                  <ShieldCheck size={13} />
                  {s.license}
                </span>
                <span>{s.creator}</span>
              </div>
            </div>
          </button>
        ))}
      </div>
      {!visible.length && (
        <p className="empty-library">
          No source titles match this filter. Try a visual description in
          semantic search above.
        </p>
      )}
      <section className="attribution-box">
        <Info size={20} />
        <div>
          <h3>Bundled demonstration media</h3>
          <p>{manifest?.attribution}</p>
          <a
            href="https://mango.blender.org/sharing/"
            target="_blank"
            rel="noreferrer"
          >
            Tears of Steel license
            <ArrowUpRight size={13} />
          </a>
        </div>
      </section>
    </>
  );
}
