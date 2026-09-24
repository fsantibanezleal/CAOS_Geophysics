/** Piecewise-linear isosurface on the actual cell-centre field; no new physical data. */
export function isosurface(
  values: number[],
  shape: number[],
  origin: number[],
  spacing: number[],
  level: number,
): Float32Array {
  const [nz, ny, nx] = shape;
  if (values.length !== nx * ny * nz || !Number.isFinite(level))
    throw Error("Invalid scalar volume");
  const corners = [
    [0, 0, 0],
    [1, 0, 0],
    [1, 1, 0],
    [0, 1, 0],
    [0, 0, 1],
    [1, 0, 1],
    [1, 1, 1],
    [0, 1, 1],
  ];
  const tetra = [
    [0, 5, 1, 6],
    [0, 1, 2, 6],
    [0, 2, 3, 6],
    [0, 3, 7, 6],
    [0, 7, 4, 6],
    [0, 4, 5, 6],
  ];
  const output: number[] = [];
  for (let iz = -1; iz < nz; iz++)
    for (let iy = -1; iy < ny; iy++)
      for (let ix = -1; ix < nx; ix++) {
        const nodes = corners.map(([dx, dy, dz]) => {
          const x = ix + dx,
            y = iy + dy,
            z = iz + dz;
          const v =
            x < 0 || y < 0 || z < 0 || x >= nx || y >= ny || z >= nz
              ? 0
              : values[(z * ny + y) * nx + x];
          return {
            v,
            p: [
              origin[0] + Math.max(0, Math.min(nx, x + 0.5)) * spacing[0],
              origin[2] + Math.max(0, Math.min(nz, z + 0.5)) * spacing[2],
              origin[1] + Math.max(0, Math.min(ny, y + 0.5)) * spacing[1],
            ],
          };
        });
        if (nodes.every((n) => n.v < level) || nodes.every((n) => n.v >= level))
          continue;
        const edge = (a: number, b: number) => {
          const t = (level - nodes[a].v) / (nodes[b].v - nodes[a].v);
          return nodes[a].p.map((p, k) => (p + t * (nodes[b].p[k] - p)) / 1000);
        };
        for (const ids of tetra) {
          const inside = ids.filter((k) => nodes[k].v >= level),
            outside = ids.filter((k) => nodes[k].v < level);
          if (!inside.length || !outside.length) continue;
          const direction = [0, 1, 2].map(
            (axis) =>
              outside.reduce((sum, k) => sum + nodes[k].p[axis], 0) /
                outside.length -
              inside.reduce((sum, k) => sum + nodes[k].p[axis], 0) /
                inside.length,
          );
          const emit = (a: number[], b: number[], c: number[]) => {
            const u = b.map((v, k) => v - a[k]),
              v = c.map((v, k) => v - a[k]);
            const normal = [
              u[1] * v[2] - u[2] * v[1],
              u[2] * v[0] - u[0] * v[2],
              u[0] * v[1] - u[1] * v[0],
            ];
            if (normal.reduce((sum, n, k) => sum + n * direction[k], 0) < 0)
              output.push(...a, ...c, ...b);
            else output.push(...a, ...b, ...c);
          };
          if (inside.length === 1) {
            emit(
              ...(outside.map((k) => edge(inside[0], k)) as [
                number[],
                number[],
                number[],
              ]),
            );
          } else if (inside.length === 3) {
            emit(
              ...(inside.map((k) => edge(outside[0], k)).reverse() as [
                number[],
                number[],
                number[],
              ]),
            );
          } else if (inside.length === 2) {
            const a = edge(inside[0], outside[0]),
              b = edge(inside[0], outside[1]),
              c = edge(inside[1], outside[0]),
              d = edge(inside[1], outside[1]);
            emit(a, b, c);
            emit(b, d, c);
          }
        }
      }
  return new Float32Array(output);
}
