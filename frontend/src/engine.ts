export type CaseParams = { anomaly: number; depth: number; conductivity: number; noise: number; frequency: number; angle_deg: number };

export type LiveResult = {
  x: number[]; z: number[]; density: number[]; susceptibility: number[]; gravity: number[]; magnetic: number[]; frequency: number[]; resistivity: number[]; phase: number[]; wave: number[]; residual: number[]; cross: number[]; uncertainty: number[];
};

export const CASES: Array<{ id: string; category: string; method: string; description: string; params: CaseParams }> = [
  ['GRAVITY_INTRUSION','potential fields','Gravity prism inversion','Dense body with a shallow gravity signature.',1.35,420,2.2,.025,0,0], ['GRAVITY_DEEP_BODY','potential fields','Depth-weighted gravity','Deeper target with non-unique amplitude recovery.',1.10,1080,1.9,.035,18,0], ['GRAVITY_NOISY','potential fields','Robust gravity residual','Noisy acquisition for regularization stress testing.',1.65,680,2.8,.09,42,0], ['GRAVITY_TILTED','potential fields','Rotated gravity survey','Oblique survey geometry tests coordinate conventions.',.90,760,1.5,.02,66,0],
  ['MAGNETIC_DYKE','potential fields','Induced magnetics','Narrow susceptibility contrast under an inducing field.',1.30,360,2.8,.025,25,0], ['MAGNETIC_REMANENCE','potential fields','Field-direction sensitivity','Direction mismatch exposes scalar inversion limits.',1.55,720,3.4,.06,54,0], ['MAGNETIC_DEEP','potential fields','Sparse magnetic body','Deep compact body with weak surface response.',.78,1180,1.2,.04,72,0], ['MAGNETIC_NOISY','potential fields','Magnetic IRLS stress','Outlier-prone anomaly for robust misfit comparison.',1.80,590,4.2,.12,38,0],
  ['MT_RESISTIVE','electromagnetics','Layered resistive cap','High-resistivity layer over a conductive basement.',1,380,.45,.015,0,0], ['MT_CONDUCTIVE','electromagnetics','Layered conductive lens','Conductive target with frequency-dependent skin depth.',1.25,620,4.8,.025,0,0], ['MT_MIXED','electromagnetics','Physics-guided MT','Mixed layers for differentiable impedance inversion.',1.45,880,1.8,.04,0,0], ['MT_NOISY','electromagnetics','MT uncertainty bands','Large error bars test uncertainty communication.',.92,1040,2.6,.11,0,0],
  ['FWI_LAYERED','seismic','Acoustic layered FWI','Low-contrast model for frequency continuation.',.90,520,1.7,.02,0,0], ['FWI_FAULT','seismic','Acoustic fault FWI','Laterally varying target and shot residual.',1.40,760,2,.035,0,0], ['FWI_CYCLE_SKIP','seismic','Cycle-skipping diagnostic','Sparse low-frequency content makes phase errors visible.',1.65,980,2.5,.065,0,0], ['FWI_NOISY','seismic','Robust FWI residual','Noise and taper sensitivity experiment.',1.05,660,1.2,.12,0,0],
  ['JOINT_SHARED','joint inversion','Cross-gradient agreement','Gravity and magnetics share a structural boundary.',1.30,640,2.3,.035,40,0], ['JOINT_CONFLICT','joint inversion','Cross-gradient conflict','Different physics illuminate different parts of the model.',1.70,860,3.2,.07,60,0], ['LEARNED_CNN','learned methods','CNN field prior','Convolutional prior evaluated against a held-out synthetic case.',1.15,540,2,.05,30,0], ['LEARNED_AUTOENCODER','learned methods','Autoencoder novelty','Latent reconstruction error highlights novel structure.',.95,910,1.6,.045,15,0],
].map(([id,category,method,description,anomaly,depth,conductivity,noise,angle_deg]) => ({ id: String(id), category: String(category), method: String(method), description: String(description), params: { anomaly: Number(anomaly), depth: Number(depth), conductivity: Number(conductivity), noise: Number(noise), frequency: 18, angle_deg: Number(angle_deg) } }));

export function makeLiveResult(p: CaseParams, seed = 42, n = 32): LiveResult {
  const x = Array.from({ length: n }, (_, i) => -1600 + (3200 * i) / (n - 1));
  const z = Array.from({ length: 24 }, (_, i) => (1800 * i) / 23);
  const density: number[] = [], susceptibility: number[] = [], cross: number[] = [], uncertainty: number[] = [];
  for (let iz = 0; iz < z.length; iz++) for (let ix = 0; ix < x.length; ix++) {
    const body = Math.exp(-(((x[ix] - .32 * p.depth) ** 2) / (2 * 430 ** 2) + ((z[iz] - p.depth) ** 2) / (2 * 260 ** 2))) + .55 * Math.exp(-(((x[ix] + .45 * p.depth) ** 2) / (2 * 260 ** 2) + ((z[iz] - 1.18 * p.depth) ** 2) / (2 * 180 ** 2)));
    const d = p.anomaly * body, s = .01 * p.anomaly * body * (1 + .15 * Math.sin(x[ix] / 280));
    density.push(d); susceptibility.push(s); cross.push(Math.abs(d * s) * .02); uncertainty.push(p.noise * (1 + z[iz] / 1800));
  }
  const gravity: number[] = [], magnetic: number[] = [];
  const theta = p.angle_deg * Math.PI / 180;
  for (const xo of x.concat(x.slice(0, 16))) {
    let g = 0, m = 0;
    for (let iz = 0; iz < z.length; iz++) for (let ix = 0; ix < x.length; ix++) { const dx = xo - x[ix], dz = 1 + z[iz], r = Math.pow(dx * dx + dz * dz, 1.5); g += dz / r * density[iz * n + ix]; m += (dx * Math.cos(theta) + dz * Math.sin(theta)) / r * susceptibility[iz * n + ix]; }
    gravity.push(g * 22); magnetic.push(m * 120000);
  }
  const frequency = Array.from({ length: 24 }, (_, i) => .01 * Math.pow(10000, i / 23));
  const resistivity = frequency.map((f) => 18 + 42 / (1 + Math.pow(f / (p.conductivity + .2), .7)) + 8 * Math.exp(-f / 2));
  const phase = frequency.map((f) => 42 + 17 * Math.atan(Math.log10(f + .01) / 2) - p.conductivity * 1.2);
  const wave = Array.from({ length: 96 }, (_, i) => Math.exp(-(((i - 35) / 11) ** 2)) * Math.sin(i * p.frequency * .018));
  const residual = wave.map((v, i) => v * (.18 + p.noise) + .03 * Math.sin(i * .31 + seed));
  return { x, z, density, susceptibility, gravity, magnetic, frequency, resistivity, phase, wave, residual, cross, uncertainty };
}
