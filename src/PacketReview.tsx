import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  CheckCheck,
  FileArchive,
  Fingerprint,
  LoaderCircle,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { asset } from "./paths";
import { verifyEvidencePacket, type PacketReview as Review } from "./packet";

export default function PacketReview() {
  const [review, setReview] = useState<Review | null>(null);
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [label, setLabel] = useState("");
  const [selected, setSelected] = useState(0);
  const [pairIndex, setPairIndex] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const request = useRef(0);
  useEffect(
    () => () => {
      request.current++;
    },
    [],
  );
  useEffect(() => {
    const next: Record<string, string> = {};
    if (review)
      for (const [name, bytes] of Object.entries(review.images)) {
        next[name] = URL.createObjectURL(
          new Blob([new Uint8Array(bytes).buffer], { type: "image/jpeg" }),
        );
      }
    setUrls(next);
    return () => Object.values(next).forEach((url) => URL.revokeObjectURL(url));
  }, [review]);

  async function inspect(file?: File) {
    if (busy) return;
    const id = ++request.current;
    setBusy(true);
    setError("");
    setReview(null);
    setSelected(0);
    setPairIndex(0);
    const filename = file?.name || "traceback-evidence.zip";
    setLabel(filename);
    try {
      if (file && file.size > 32 * 1024 * 1024)
        throw Error("Choose a packet smaller than 32 MB.");
      let bytes: Uint8Array;
      if (file) bytes = new Uint8Array(await file.arrayBuffer());
      else {
        const response = await fetch(
          asset("/downloads/traceback-evidence.zip"),
          { signal: AbortSignal.timeout(15000) },
        );
        if (!response.ok)
          throw Error("The sample packet could not be downloaded.");
        bytes = new Uint8Array(await response.arrayBuffer());
      }
      const result = await verifyEvidencePacket(bytes);
      if (id === request.current) setReview(result);
    } catch (e) {
      if (id === request.current)
        setError(
          e instanceof Error ? e.message : "The packet could not be verified.",
        );
    } finally {
      if (id === request.current) setBusy(false);
    }
  }
  const match = review?.matches[selected];
  const pair = match?.pairs[pairIndex];
  return (
    <>
      <section className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="tiny-line" /> PORTABLE EVIDENCE, LOCALLY CHECKED
          </div>
          <h1>Inspect what was shared.</h1>
          <p>
            Open a Traceback evidence packet. Verify its files and review the
            included frame pairs in your browser.
          </p>
        </div>
      </section>
      <section
        className="packet-upload panel"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (!busy && e.dataTransfer.files[0])
            void inspect(e.dataTransfer.files[0]);
        }}
      >
        <div className="packet-upload-icon">
          <FileArchive size={30} />
        </div>
        <div className="packet-upload-copy">
          <h2>Drop an evidence ZIP here</h2>
          <p>
            Up to 32 MB. Files stay in this browser; nothing is uploaded. A
            sample packet is available below.
          </p>
        </div>
        <div className="packet-upload-actions">
          <button
            className="button primary"
            disabled={busy}
            onClick={() => input.current?.click()}
          >
            <Upload size={16} /> Choose packet
          </button>
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => void inspect()}
          >
            <ShieldCheck size={16} /> Verify sample packet
          </button>
        </div>
        <input
          ref={input}
          hidden
          type="file"
          accept=".zip,application/zip"
          aria-label="Choose an evidence packet"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void inspect(file);
            e.target.value = "";
          }}
        />
      </section>
      <p className="packet-boundary">
        <Fingerprint size={16} /> Checksums verify internal file integrity. They
        are not signatures, proof of authorship, or a new source analysis.
      </p>
      {busy && (
        <div className="packet-progress panel" role="status">
          <LoaderCircle className="spin" size={20} /> Checking the report and
          every included frame…
        </div>
      )}
      {error && (
        <div className="packet-error panel" role="alert">
          <h3>Packet verification stopped</h3>
          <p>{error}</p>
          <p>
            No verified result was produced. Choose another packet to try again.
          </p>
        </div>
      )}
      {review && (
        <>
          <section
            className="packet-success panel"
            aria-label="Packet verification result"
          >
            <CheckCheck size={28} />
            <div>
              <span className="eyebrow">INTEGRITY CHECK COMPLETE</span>
              <h2>Report + {review.imageCount} frame checksums match.</h2>
              <p>{label} · Analysis was not rerun.</p>
            </div>
            <span className="pill neutral">VERIFIED IN THIS BROWSER</span>
          </section>
          <section className="packet-metadata panel">
            <h2>What this packet reports</h2>
            <dl>
              <div>
                <dt>Query filename</dt>
                <dd>{review.filename}</dd>
              </div>
              <div>
                <dt>Reported source matches</dt>
                <dd>{review.matches.length}</dd>
              </div>
              <div>
                <dt>Retrieval model</dt>
                <dd>{review.model}</dd>
              </div>
              <div>
                <dt>Model revision</dt>
                <dd className="mono">{review.modelRevision}</dd>
              </div>
              <div>
                <dt>Query video SHA-256</dt>
                <dd className="mono">{review.queryHash}</dd>
              </div>
              <div>
                <dt>Engine fingerprint</dt>
                <dd className="mono">{review.engineFingerprint}</dd>
              </div>
            </dl>
            <p>
              The original videos are not included. Their reported hashes
              identify the analyzed inputs; this check covers the report and
              included images.
            </p>
          </section>
          {review.matches.length > 0 && (
            <section className="packet-evidence panel">
              <header>
                <div>
                  <span className="eyebrow">INSPECT THE INCLUDED FRAMES</span>
                  <h2>Recorded visual correspondences</h2>
                </div>
              </header>
              <div
                className="packet-match-tabs"
                role="group"
                aria-label="Reported source matches"
              >
                {review.matches.map((result, i) => (
                  <button
                    key={i}
                    className={i === selected ? "selected" : ""}
                    aria-pressed={i === selected}
                    onClick={() => {
                      setSelected(i);
                      setPairIndex(0);
                    }}
                  >
                    {result.title}
                  </button>
                ))}
              </div>
              {match && (
                <>
                  <div className="packet-match-summary">
                    <strong>{match.title}</strong>
                    <span>{match.support} reported supporting frames</span>
                    <span>
                      {match.sourceStart.toFixed(2)}–
                      {match.sourceEnd.toFixed(2)}s source interval
                    </span>
                    <span>
                      {match.speedReliable
                        ? `${match.speed.toFixed(2)}× reported speed`
                        : "Playback estimate uncertain"}
                    </span>
                  </div>
                  {pair ? (
                    <>
                      <div className="packet-pair">
                        <figure>
                          <img
                            src={urls[pair.queryImage]}
                            alt={`Included query frame at ${pair.queryTime.toFixed(2)} seconds`}
                          />
                          <figcaption>
                            Query · {pair.queryTime.toFixed(2)}s
                          </figcaption>
                        </figure>
                        <figure>
                          <img
                            src={urls[pair.sourceImage]}
                            alt={`Included source frame at ${pair.sourceTime.toFixed(2)} seconds`}
                          />
                          <figcaption>
                            Source · {pair.sourceTime.toFixed(2)}s
                          </figcaption>
                        </figure>
                      </div>
                      <div
                        className="packet-pair-picker"
                        role="group"
                        aria-label="Included frame pairs"
                      >
                        {match.pairs.map((_, i) => (
                          <button
                            key={i}
                            aria-label={`Review included pair ${i + 1}`}
                            aria-pressed={i === pairIndex}
                            onClick={() => setPairIndex(i)}
                          >
                            {i + 1}
                          </button>
                        ))}
                        <span>
                          Pair {pairIndex + 1} of {match.pairs.length} ·{" "}
                          {pair.inliers} reported geometric inliers
                        </span>
                      </div>
                    </>
                  ) : (
                    <p>This source entry contains no inspected frame pair.</p>
                  )}
                  <p className="packet-attribution">
                    Reported source credit: {match.creator}. Rights label:{" "}
                    {match.license}. These labels are supplied metadata, not
                    independently verified rights.
                  </p>
                </>
              )}
            </section>
          )}
          {!review.matches.length && (
            <section className="packet-metadata panel">
              <h2>No source match in this report</h2>
              <p>
                The packet records an abstention within its indexed library.
                This does not establish that the clip has no source elsewhere.
              </p>
            </section>
          )}
          <details className="packet-audit panel">
            <summary>Checksums and report limitations</summary>
            <dl>
              <div>
                <dt>This ZIP SHA-256</dt>
                <dd className="mono">{review.packetHash}</dd>
              </div>
              <div>
                <dt>report.json SHA-256</dt>
                <dd className="mono">{review.reportHash}</dd>
              </div>
            </dl>
            <ul>
              {review.limitations.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
            <p>
              A person who replaces both the data and its checksums can create a
              different internally consistent packet. Use trusted distribution
              or a separate signature when authorship matters.
            </p>
          </details>
        </>
      )}
      <div className="packet-download">
        <a href={asset("/downloads/traceback-evidence.zip")} download>
          <ArrowDownToLine size={15} /> Download the sample packet
        </a>
        <span>
          Also verifiable with scripts/verify_packet.py in the public
          repository.
        </span>
      </div>
    </>
  );
}
