const { test } = require("node:test");
const assert = require("node:assert/strict");
test("RGB565 encoding preserves color order and composites alpha", async () => {
  const { encodeRgb565 } = await import("../renderer/src/background-codec.mjs");
  assert.equal(
    Buffer.from(
      encodeRgb565(
        new Uint8Array([
          255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 255, 255, 255, 255,
          255, 255, 255, 0,
        ]),
      ),
    ).toString("hex"),
    "f80007e0001fffff0000",
  );
  assert.throws(() => encodeRgb565(new Uint8Array(3)));
});
test("center crop fills portrait watch without stretching the source", async () => {
  const { cropRect } = await import("../renderer/src/background-codec.mjs");
  const [x, y, w, h] = cropRect(800, 400, 240, 284);
  assert.equal(y, 0);
  assert.equal(h, 400);
  assert.ok(x > 0);
  assert.ok(Math.abs(w / h - 240 / 284) < 1e-12);
  assert.deepEqual(cropRect(240, 284, 240, 284), [0, 0, 240, 284]);
  assert.throws(() => cropRect(0, 10, 240, 284));
});
