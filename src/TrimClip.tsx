import { useEffect, useRef, useState } from "react";
import { ArrowRight, LoaderCircle, Play, Scissors } from "lucide-react";
import { timestamp } from "./internet";

type Props = {
  src: string;
  duration: number;
  filename: string;
  busy: boolean;
  message: string;
  onSubmit: (start: number, duration: number) => void;
  onCancel: () => void;
};

export default function TrimClip({
  src,
  duration,
  filename,
  busy,
  message,
  onSubmit,
  onCancel,
}: Props) {
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(Math.min(60, duration));
  const [startText, setStartText] = useState("0");
  const [endText, setEndText] = useState(String(Math.min(60, duration)));
  const [previewError, setPreviewError] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const length = end - start;
  const valid =
    startText.trim() !== "" &&
    endText.trim() !== "" &&
    Number.isFinite(Number(startText)) &&
    Number.isFinite(Number(endText)) &&
    Number(startText) >= 0 &&
    Number(endText) <= duration + 0.001 &&
    Number(endText) - Number(startText) >= 2 &&
    Number(endText) - Number(startText) <= 60 + 1e-6;

  useEffect(() => {
    heading.current?.focus();
  }, []);
  function select(a: number, b: number) {
    setStart(a);
    setEnd(b);
    setStartText(String(Math.round(a * 1000) / 1000));
    setEndText(String(Math.round(b * 1000) / 1000));
    if (video.current) {
      video.current.pause();
      video.current.currentTime = a;
    }
  }
  function updateTimes(a: string, b: string) {
    setStartText(a);
    setEndText(b);
    const x = Number(a),
      y = Number(b);
    if (
      a.trim() &&
      b.trim() &&
      Number.isFinite(x) &&
      Number.isFinite(y) &&
      x >= 0 &&
      y <= duration + 0.001 &&
      y - x >= 2 &&
      y - x <= 60 + 1e-6
    ) {
      setStart(x);
      setEnd(y);
      if (video.current) {
        video.current.pause();
        video.current.currentTime = x;
      }
    }
  }
  async function preview() {
    if (!video.current) return;
    video.current.currentTime = start;
    try {
      await video.current.play();
    } catch {
      setPreviewError(true);
    }
  }
  return (
    <section className="clip-trimmer" aria-labelledby="trim-title">
      <div className="trim-preview">
        <video
          ref={video}
          src={src}
          controls
          playsInline
          preload="metadata"
          aria-label="Full video preview"
          onError={() => setPreviewError(true)}
          onPlay={() => {
            if (
              video.current &&
              (video.current.currentTime < start ||
                video.current.currentTime >= end)
            )
              video.current.currentTime = start;
          }}
          onTimeUpdate={() => {
            if (
              video.current &&
              !video.current.paused &&
              video.current.currentTime >= end
            )
              video.current.pause();
          }}
        />
        <p>
          {filename} <span>· {timestamp(duration)} total</span>
        </p>
        {previewError && (
          <p role="status">
            Preview unavailable in this browser. You can still choose start and
            end times below.
          </p>
        )}
      </div>
      <form
        className="trim-controls"
        onSubmit={(e) => {
          e.preventDefault();
          if (valid && !busy)
            onSubmit(
              Number(startText),
              Math.min(60, Number(endText) - Number(startText)),
            );
        }}
      >
        <span className="eyebrow">
          <Scissors size={15} /> PICK YOUR CLIP
        </span>
        <h2 id="trim-title" ref={heading} tabIndex={-1}>
          Choose the part to search
        </h2>
        <p>
          Move the window to the moment you want. Search up to 60 seconds of
          this video.
        </p>
        <fieldset disabled={busy}>
          <legend className="visually-hidden">Select video interval</legend>
          <div className="trim-window" aria-hidden="true">
            <span
              style={{
                left: `${(start / duration) * 100}%`,
                width: `${(length / duration) * 100}%`,
              }}
            />
          </div>
          <label htmlFor="clip-start">Move clip window</label>
          <input
            id="clip-start"
            type="range"
            min="0"
            max={Math.max(0, duration - length)}
            step="any"
            value={start}
            onChange={(e) => {
              const next = Math.min(
                duration - length,
                Math.round(Number(e.target.value) * 10) / 10,
              );
              select(next, next + length);
            }}
          />
          <div className="trim-timeline">
            <span>0:00</span>
            <span>{timestamp(duration)}</span>
          </div>
          <div className="trim-times">
            <label>
              Start (seconds)
              <input
                type="number"
                min="0"
                max={duration - 2}
                step="any"
                value={startText}
                onChange={(e) => updateTimes(e.target.value, endText)}
              />
            </label>
            <label>
              End (seconds)
              <input
                type="number"
                min="2"
                max={duration}
                step="any"
                value={endText}
                onChange={(e) => updateTimes(startText, e.target.value)}
              />
            </label>
          </div>
          <p className="trim-selection" aria-live="polite">
            {valid
              ? `${timestamp(Number(startText))} → ${timestamp(Number(endText))} · ${(Number(endText) - Number(startText)).toFixed(1)} seconds selected`
              : "Choose a section between 2 and 60 seconds within the video."}
          </p>
          <div className="trim-actions">
            <button
              className="button secondary"
              type="button"
              disabled={!valid || previewError}
              onClick={() => void preview()}
            >
              <Play size={16} /> Preview selection
            </button>
            <button className="button primary" type="submit" disabled={!valid}>
              Search this clip <ArrowRight size={16} />
            </button>
          </div>
          <button className="trim-cancel" type="button" onClick={onCancel}>
            Choose another video
          </button>
        </fieldset>
        {busy && (
          <div className="trim-progress" role="status">
            <LoaderCircle size={20} className="spin" />
            <span>
              {message}
              <small>
                Keep this tab open. Local processing can take a few minutes.
              </small>
            </span>
          </div>
        )}
      </form>
    </section>
  );
}
