import type { MtCurves, MtResult } from "../api/mt-contracts";
export type MtQuantity = "real" | "imag" | "apparent" | "phase";
export const quantityUnit = (q: MtQuantity) => q === "apparent" ? "Ω m" : q === "phase" ? "°" : "Ω E/H";
/** The inverse fits XY only. YX here is already sign-corrected by the parser. */
export function mtResidual(result: MtResult, component: "xy" | "yx", quantity: "real" | "imag", normalized: boolean) {
  if (!result.inverse) throw new Error("M05 has no prediction or residual");
  const observed = result.screen.observed[component], predicted = result.inverse.methods["mt-lm"].predicted;
  return observed[quantity].map((v, i) => (v - predicted[quantity][i]) / (normalized ? observed.sigma_real_imag_ohm[i] : 1));
}
export function partition(values: number[], mask: boolean[], training: boolean) {return values.map((v,i)=>mask[i]===training?v:NaN);}
export function frequencyAxis(frequency: number[], period: boolean) {return frequency.map(v=>period?1/v:v);}
export function curveQuantity(curves: MtCurves, quantity: MtQuantity) {return curves[quantity];}
