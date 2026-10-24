// A minimal PNG decoder for the gate's own screenshots (8-bit RGB or RGBA, not interlaced: what Chromium writes).
// The gate decides on painted pixels (G6), never on the host element's box, so it reads the pixels itself instead of
// trusting what a renderer says it drew. No dependency: zlib is in Node.

import { inflateSync } from 'node:zlib';

const SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

/** @returns {{ width: number, height: number, data: Buffer }} RGBA, 4 bytes per pixel, row-major. */
export function decodePng(buf) {
  if (!buf.subarray(0, 8).equals(SIGNATURE)) throw new Error('decodePng: not a PNG');
  let pos = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  let interlace = 0;
  const idat = [];
  while (pos < buf.length) {
    const len = buf.readUInt32BE(pos);
    const type = buf.toString('ascii', pos + 4, pos + 8);
    const data = buf.subarray(pos + 8, pos + 8 + len);
    pos += 12 + len;
    if (type === 'IHDR') {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      bitDepth = data[8];
      colorType = data[9];
      interlace = data[12];
    } else if (type === 'IDAT') idat.push(data);
    else if (type === 'IEND') break;
  }
  if (bitDepth !== 8 || interlace !== 0 || (colorType !== 2 && colorType !== 6)) {
    throw new Error(`decodePng: unsupported PNG (bit depth ${bitDepth}, colour type ${colorType}, interlace ${interlace})`);
  }
  const bpp = colorType === 6 ? 4 : 3;
  const stride = width * bpp;
  const raw = inflateSync(Buffer.concat(idat));
  const out = Buffer.alloc(width * height * 4);
  let prev = Buffer.alloc(stride);
  for (let y = 0; y < height; y += 1) {
    const filter = raw[y * (stride + 1)];
    const line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
    const cur = Buffer.alloc(stride);
    for (let x = 0; x < stride; x += 1) {
      const a = x >= bpp ? cur[x - bpp] : 0;
      const b = prev[x];
      const c = x >= bpp ? prev[x - bpp] : 0;
      let v = line[x];
      if (filter === 1) v += a;
      else if (filter === 2) v += b;
      else if (filter === 3) v += (a + b) >> 1;
      else if (filter === 4) {
        const p = a + b - c;
        const pa = Math.abs(p - a);
        const pb = Math.abs(p - b);
        const pc = Math.abs(p - c);
        v += pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
      }
      cur[x] = v & 255;
    }
    for (let x = 0; x < width; x += 1) {
      const o = (y * width + x) * 4;
      out[o] = cur[x * bpp];
      out[o + 1] = cur[x * bpp + 1];
      out[o + 2] = cur[x * bpp + 2];
      out[o + 3] = bpp === 4 ? cur[x * bpp + 3] : 255;
    }
    prev = cur;
  }
  return { width, height, data: out };
}

/**
 * The painted extent of a region of an image: the bounding box of the pixels that differ from the region's
 * background, taken as the most frequent colour along the region's border ring. A uniform region (nothing drawn)
 * returns null.
 * @param {{ width: number, height: number, data: Buffer }} img
 * @param {{ x: number, y: number, w: number, h: number }} r region in image pixels
 */
export function paintedBox(img, r, threshold = 24) {
  const x0 = Math.max(0, Math.floor(r.x));
  const y0 = Math.max(0, Math.floor(r.y));
  const x1 = Math.min(img.width, Math.ceil(r.x + r.w));
  const y1 = Math.min(img.height, Math.ceil(r.y + r.h));
  if (x1 - x0 < 2 || y1 - y0 < 2) return null;
  const d = img.data;
  const counts = new Map();
  const vote = (x, y) => {
    const o = (y * img.width + x) * 4;
    const key = ((d[o] >> 3) << 10) | ((d[o + 1] >> 3) << 5) | (d[o + 2] >> 3);
    const e = counts.get(key);
    if (e) {
      e.n += 1;
      e.r += d[o];
      e.g += d[o + 1];
      e.b += d[o + 2];
    } else counts.set(key, { n: 1, r: d[o], g: d[o + 1], b: d[o + 2] });
  };
  for (let x = x0; x < x1; x += 1) {
    vote(x, y0);
    vote(x, y1 - 1);
  }
  for (let y = y0; y < y1; y += 1) {
    vote(x0, y);
    vote(x1 - 1, y);
  }
  let best = null;
  for (const e of counts.values()) if (!best || e.n > best.n) best = e;
  const br = best.r / best.n;
  const bg = best.g / best.n;
  const bb = best.b / best.n;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -1;
  let maxY = -1;
  let painted = 0;
  for (let y = y0; y < y1; y += 1) {
    let o = (y * img.width + x0) * 4;
    for (let x = x0; x < x1; x += 1, o += 4) {
      if (Math.abs(d[o] - br) > threshold || Math.abs(d[o + 1] - bg) > threshold || Math.abs(d[o + 2] - bb) > threshold) {
        painted += 1;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  if (maxX < 0) return null;
  return { x: minX, y: minY, w: maxX - minX + 1, h: maxY - minY + 1, painted };
}

/** The area of a union of rectangles, rasterised on a grid of `cell` pixels. */
export function unionArea(rects, width, height, cell = 4) {
  const cols = Math.ceil(width / cell);
  const rows = Math.ceil(height / cell);
  const grid = new Uint8Array(cols * rows);
  for (const r of rects) {
    const c0 = Math.max(0, Math.floor(r.x / cell));
    const c1 = Math.min(cols, Math.ceil((r.x + r.w) / cell));
    const r0 = Math.max(0, Math.floor(r.y / cell));
    const r1 = Math.min(rows, Math.ceil((r.y + r.h) / cell));
    for (let y = r0; y < r1; y += 1) grid.fill(1, y * cols + c0, y * cols + c1);
  }
  let n = 0;
  for (let i = 0; i < grid.length; i += 1) n += grid[i];
  return n * cell * cell;
}
