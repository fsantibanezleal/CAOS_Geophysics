import { useId } from "react";
import { Figure, useShellLang } from "@fasl-work/caos-app-shell";
import type { MTMethod } from "../data/online-mt-course";

/** Original physical schematics, not measured acquisition geometry or recovered geology. */
export function OnlineMTDiagram({ method }: { method: MTMethod }) {
  const id = useId();
  const es = useShellLang() === "es";
  const t = (en: string, sp: string) => es ? sp : en;
  const title = method === "m05"
    ? t("Horizontal fields in a declared common tensor frame", "Campos horizontales en marco tensorial común declarado")
    : t("Plane-wave diffusion through a fixed cover and infinite basement", "Difusión de onda plana por cubierta fija y basamento infinito");
  const caption = method === "m05"
    ? t("Physical assumption schematic in the horizontal x-y plane: +x upward, +y rightward. Not a field measurement or recovered section. Arrow lengths do not encode data amplitudes.", "Esquema de supuestos físicos en plano horizontal x-y: +x arriba, +y a la derecha. No es medición de campo ni sección recuperada. Longitudes de flecha no representan amplitudes.")
    : t("Assumed x-z viewing section: +x rightward, +y out of the page toward the viewer (dot-in-circle), +z downward. Ex and Hy are orthogonal horizontal fields; depth diffusion is downward. Not a field measurement or recovered section. Glyph sizes and arrow lengths do not encode data amplitudes.", "Sección de vista x-z supuesta: +x a la derecha, +y fuera de la página hacia el observador (punto en círculo), +z hacia abajo. Ex y Hy son campos horizontales ortogonales; difusión en profundidad hacia abajo. No es medición de campo ni sección recuperada. Tamaños de símbolos y longitudes de flecha no representan amplitudes.");
  return <Figure caption={caption}>
    <svg data-mt-physics={method} className="method-diagram" viewBox="0 0 480 390" role="img" aria-label={title} style={{ maxWidth: 640 }}>
      <title>{title}</title>
      <defs><marker id={id} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="var(--color-accent)" /></marker></defs>
      {method === "m05" ? <>
        <rect x="20" y="20" width="440" height="225" rx="8" className="diagram-box" />
        <path d="M240 206V55 M240 206H412" className="diagram-highlight" markerEnd={`url(#${id})`} />
        <path d="M240 206V55" className="diagram-highlight" markerEnd={`url(#${id})`} />
        <text x="254" y="59">x</text><text x="419" y="211">y</text>
        <path d="M135 135H205 M305 166V96" className="diagram-highlight" markerEnd={`url(#${id})`} />
        <text x="132" y="119">Eᵧ (V/m)</text><text x="319" y="138">Hₓ (A/m)</text>
        <circle cx="240" cy="206" r="5" fill="var(--color-fg)" />
        <text x="42" y="44">{t("Supplied frame", "Marco suministrado")}</text>
        <text x="42" y="232" className="diagram-muted">{t("North only if documented", "Norte sólo si documentado")}</text>
        <rect x="20" y="263" width="440" height="107" rx="8" className="diagram-active" />
        <text x="42" y="289">E = ZH · Z (Ω)</text>
        <text x="42" y="321">{t("1D: Zxx = Zyy = 0; Zyx = −Zxy", "1D: Zxx = Zyy = 0; Zyx = −Zxy")}</text>
        <text x="42" y="354" className="diagram-muted">{t("Full tensor + marginal σ → QC", "Tensor completo + σ marginal → QC")}</text>
      </> : <>
        <text x="20" y="28">{t("Horizontal plane-wave fields", "Campos horizontales de onda plana")}</text>
        <path data-mt-direction="x-right" d="M50 70H155" className="diagram-highlight" markerEnd={`url(#${id})`} />
        <text x="55" y="57">Eₓ (+x)</text>
        <g data-mt-direction="y-out-of-plane" aria-label={t("Positive Hy toward viewer", "Hy positivo hacia observador")}>
          <circle cx="250" cy="70" r="12" className="diagram-highlight" />
          <circle cx="250" cy="70" r="3" fill="var(--color-accent)" />
        </g>
        <text x="273" y="77">Hᵧ (+y)</text>
        <path d="M20 94H460" className="diagram-edge" />
        <rect x="60" y="95" width="360" height="108" className="diagram-active" />
        <rect x="60" y="204" width="360" height="128" className="diagram-box" />
        <text x="80" y="128">{t("Cover ρ₀ (Ω m)", "Cubierta ρ₀ (Ω m)")}</text>
        <text x="80" y="155">{t("Fixed h₀ (m)", "h₀ fijo (m)")}</text>
        <text x="80" y="183">k₀h₀ · tanh(k₀h₀)</text>
        <text x="80" y="238">{t("Basement ρ₁ (Ω m)", "Basamento ρ₁ (Ω m)")}</text>
        <text x="80" y="265">{t("Infinite halfspace", "Semiespacio infinito")}</text>
        <text x="80" y="294">Z₁ = √(iωμ₀ρ₁)</text>
        <path data-mt-direction="z-down" d="M38 101V330" className="diagram-highlight" markerEnd={`url(#${id})`} />
        <path d="M441 98V201" className="diagram-highlight" markerEnd={`url(#${id})`} />
        <text x="22" y="351">{t("Depth increases downward", "Profundidad hacia abajo")}</text>
        <text x="22" y="377">{t("No inferred field boundary", "Sin frontera de campo inferida")}</text>
        <path d="M340 105C380 135 332 157 347 199C360 238 339 270 341 316" className="diagram-highlight" />
        <text x="288" y="316">e⁻ᵏᶻ</text>
      </>}
    </svg>
  </Figure>;
}
