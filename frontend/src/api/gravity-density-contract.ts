export type GravityAcceptedFrame = { density_kg_m3: number[]; phi_engine: number; kkt_normalized: number };

export function validateAcceptedFrames(frames: GravityAcceptedFrame[], terminalDensity: number[], cellCount: number): GravityAcceptedFrame[] {
  if (frames.length < 1 || frames.length > 201 || frames.some(frame => frame.density_kg_m3.length !== cellCount
      || frame.density_kg_m3.some(value => !Number.isFinite(value))
      || !Number.isFinite(frame.phi_engine) || frame.phi_engine < 0
      || !Number.isFinite(frame.kkt_normalized) || frame.kkt_normalized < 0)) {
    throw new Error("Gravity accepted-state history is invalid");
  }
  const last = frames.at(-1)!;
  if (terminalDensity.length !== cellCount || last.density_kg_m3.some((value, index) => value !== terminalDensity[index])) {
    throw new Error("Gravity accepted-state history does not end at the returned model");
  }
  return frames;
}
