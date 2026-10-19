/** Pure pixel/crop helpers shared by the UI and offline tests. */
export function encodeRgb565(rgba) {
  if (rgba.length % 4) throw new Error("Incomplete RGBA pixels");
  const bytes = new Uint8Array(rgba.length / 2);
  for (let i = 0, j = 0; i < rgba.length; i += 4) {
    const alpha = rgba[i + 3] / 255;
    const r = Math.floor(rgba[i] * alpha),
      g = Math.floor(rgba[i + 1] * alpha),
      b = Math.floor(rgba[i + 2] * alpha);
    bytes[j++] = (r & 0xf8) | (g >> 5);
    bytes[j++] = ((g & 0x1c) << 3) | (b >> 3);
  }
  return bytes;
}
export function cropRect(width, height, targetWidth, targetHeight) {
  if (
    ![width, height, targetWidth, targetHeight].every(
      (v) => Number.isFinite(v) && v > 0,
    )
  )
    throw new Error("Invalid image dimensions");
  const scale = Math.max(targetWidth / width, targetHeight / height);
  const w = targetWidth / scale,
    h = targetHeight / scale;
  return [(width - w) / 2, (height - h) / 2, w, h];
}
