import { useRef, useState } from "react";
import { ImagePlus, Upload, Square } from "lucide-react";
import { cropRect, encodeRgb565 } from "./background-codec.mjs";
import type { BackgroundStatus } from "./types";

interface Prepared {
  preview: string;
  bytes: Uint8Array;
  name: string;
}
async function prepare(file: File): Promise<Prepared> {
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type))
    throw Error("Choose a PNG, JPEG or WebP image.");
  if (file.size > 12 * 1024 * 1024)
    throw Error("Choose an image smaller than 12 MB.");
  const bitmap = await createImageBitmap(file);
  return prepareBitmap(bitmap, file.name);
}
async function prepareBitmap(
  bitmap: ImageBitmap,
  name: string,
): Promise<Prepared> {
  try {
    if (bitmap.width * bitmap.height > 24_000_000)
      throw Error("Choose an image with fewer than 24 million pixels.");
    const canvas = document.createElement("canvas");
    canvas.width = 240;
    canvas.height = 284;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw Error("Image preview is unavailable.");
    ctx.fillStyle = "#0a0a0a";
    ctx.fillRect(0, 0, 240, 284);
    ctx.imageSmoothingQuality = "high";
    const [x, y, w, h] = cropRect(bitmap.width, bitmap.height, 240, 284);
    ctx.drawImage(bitmap, x, y, w, h, 0, 0, 240, 284);
    const small = document.createElement("canvas");
    small.width = 140;
    small.height = 163;
    const thumb = small.getContext("2d");
    if (!thumb) throw Error("Image preview is unavailable.");
    thumb.drawImage(canvas, 0, 0, 140, 163);
    const original = encodeRgb565(ctx.getImageData(0, 0, 240, 284).data);
    const preview = encodeRgb565(thumb.getImageData(0, 0, 140, 163).data);
    const bytes = new Uint8Array(original.length + preview.length);
    bytes.set(original);
    bytes.set(preview, original.length);
    return { preview: canvas.toDataURL("image/png"), bytes, name };
  } finally {
    bitmap.close();
  }
}
export function BackgroundUploader({
  writable,
  status,
  busy,
  onBusy,
}: {
  writable: boolean;
  status?: BackgroundStatus;
  busy: boolean;
  onBusy: (value: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [image, setImage] = useState<Prepared>(),
    [error, setError] = useState(""),
    [preparing, setPreparing] = useState(false);
  const active =
    status?.status === "uploading" || status?.status === "verifying";
  const percent = status?.total
    ? Math.min(
        100,
        Math.floor(((status.transferred || 0) / status.total) * 100),
      )
    : 0;
  const select = async (file?: File) => {
    if (!file) return;
    setPreparing(true);
    setError("");
    try {
      setImage(await prepare(file));
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setPreparing(false);
    }
  };
  const sample = async () => {
    setPreparing(true);
    setError("");
    try {
      const source = new Image();
      source.src = new URL("sample-background.png", document.baseURI).href;
      await source.decode();
      setImage(
        await prepareBitmap(
          await createImageBitmap(source),
          "OpenWatch sample",
        ),
      );
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setPreparing(false);
    }
  };
  const upload = async () => {
    if (!image || !window.watch) return;
    setError("");
    onBusy("Preparing background");
    try {
      let part = 0;
      for (let offset = 0; offset < image.bytes.length; offset += 4096) {
        const data = btoa(
          String.fromCharCode(...image.bytes.slice(offset, offset + 4096)),
        );
        await window.watch.command("background_stage", { part: part++, data });
      }
      await window.watch.command("background_start");
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      onBusy("");
    }
  };
  const cancel = async () => {
    try {
      await window.watch?.command("background_cancel");
    } catch (e) {
      setError(String(e));
    }
  };
  return (
    <section className="panel background-panel">
      <div className="section-heading">
        <ImagePlus size={19} />
        <h3>Custom background</h3>
        <span className="subtle-badge">O20</span>
      </div>
      <div className="background-layout">
        <div className="background-preview">
          {image ? (
            <img
              src={image.preview}
              alt="Centered crop of selected watch background"
            />
          ) : (
            <div>
              <ImagePlus size={28} />
              <span>Your image here</span>
            </div>
          )}
        </div>
        <div className="background-detail">
          <h4>Make it yours.</h4>
          <p>
            Choose a photo or artwork. The preview shows the centered crop that
            will fit your watch.
          </p>
          <p className="footnote">
            240 × 284 pixels · Replaces the custom background. Built-in faces
            remain available.
          </p>
          <input
            ref={input}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            hidden
            onChange={(e) => {
              void select(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <div className="background-actions">
            <button
              className="button secondary"
              disabled={busy || active || preparing}
              onClick={() => input.current?.click()}
            >
              <ImagePlus size={15} />
              {preparing ? "Preparing preview…" : "Choose image"}
            </button>
            <button
              className="button primary"
              disabled={!writable || !image || preparing}
              onClick={upload}
            >
              <Upload size={15} />
              Upload background
            </button>
            <button
              className="text-button"
              disabled={busy || active || preparing}
              onClick={sample}
            >
              Use sample image
            </button>
          </div>
          {image && (
            <span className="footnote background-filename">
              {image.name} · stays on this computer
            </span>
          )}
          {active && (
            <div className="background-progress">
              <progress
                max={100}
                value={percent}
                aria-label="Background upload progress"
              />
              <div>
                <span>
                  {status.message} {percent}%
                </span>
                <button className="text-button" onClick={cancel}>
                  <Square size={12} />
                  Cancel upload
                </button>
              </div>
            </div>
          )}
          {!active && status && (
            <p
              role="status"
              className={
                status.status === "error"
                  ? "background-error"
                  : "background-result"
              }
            >
              {status.message}
            </p>
          )}
          {error && (
            <p role="alert" className="background-error">
              {error}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
