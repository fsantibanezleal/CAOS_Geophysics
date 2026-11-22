/** Present original electrode coordinates directly; do not rasterize or infer topography. */
export function ertSurveyPoints(sensors: number[][], quadrupole: number[]) {
  const labels = ["A", "B", "M", "N"] as const;
  const selected = new Map(quadrupole.map((electrode, i) => [electrode, labels[i]]));
  return sensors.map(([x, z], electrode) => ({
    electrode,
    x_m: x,
    elevation_m: z,
    label: selected.get(electrode) ?? null,
  }));
}
