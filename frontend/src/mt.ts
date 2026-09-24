// e^(i omega t), E/H impedance in ohms; isotropic 1D layers over a half-space.
type C = [number, number];
const add = (a: C, b: C): C => [a[0] + b[0], a[1] + b[1]];
const mul = (a: C, b: C): C => [
  a[0] * b[0] - a[1] * b[1],
  a[0] * b[1] + a[1] * b[0],
];
const div = (a: C, b: C): C => {
  const d = b[0] ** 2 + b[1] ** 2;
  return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d];
};
const tanh = (z: C): C => {
  if (z[0] > 20) return [1, 0];
  const d = Math.cosh(2 * z[0]) + Math.cos(2 * z[1]);
  return [Math.sinh(2 * z[0]) / d, Math.sin(2 * z[1]) / d];
};
export function mtForward(rho: number[], h: number[], f: number[]) {
  if (
    rho.length < 1 ||
    h.length !== rho.length - 1 ||
    [...rho, ...h, ...f].some((v) => !Number.isFinite(v) || v <= 0)
  )
    throw new Error(
      "Positive finite resistivities, thicknesses and frequencies are required.",
    );
  const mu = 4e-7 * Math.PI;
  const z = f.map((freq) => {
    const omega = 2 * Math.PI * freq;
    let s = Math.sqrt((omega * mu * rho.at(-1)!) / 2);
    let Z: C = [s, s];
    for (let j = rho.length - 2; j >= 0; j--) {
      s = Math.sqrt((omega * mu * rho[j]) / 2);
      const w: C = [s, s];
      const k = Math.sqrt((omega * mu) / rho[j] / 2) * h[j];
      const a = tanh([k, k]);
      Z = mul(w, div(add(Z, mul(w, a)), add(w, mul(Z, a))));
    }
    return Z;
  });
  return {
    real: z.map((v) => v[0]),
    imag: z.map((v) => v[1]),
    apparent: z.map(
      (v, i) => (v[0] ** 2 + v[1] ** 2) / (mu * 2 * Math.PI * f[i]),
    ),
    phase: z.map((v) => (Math.atan2(v[1], v[0]) * 180) / Math.PI),
  };
}
