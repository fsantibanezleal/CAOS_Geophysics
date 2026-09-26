import { Figure, useShellLang } from "@fasl-work/caos-app-shell";
export function MethodDiagram({ kind }: { kind: string }) {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => (es ? b : a);
  const title: Record<string, string> = {
    potential: t(
      "Prism sensitivities and the inverse parameter count",
      "Sensibilidades prismáticas y número de parámetros",
    ),
    mt: t(
      "Upward impedance recursion through a layered earth",
      "Recursión ascendente en Tierra estratificada",
    ),
    seismic: t(
      "Acoustic acquisition and the discrete gradient",
      "Adquisición acústica y gradiente discreto",
    ),
    joint: t(
      "Shared and conflicting property gradients",
      "Gradientes de propiedades compartidos y conflictivos",
    ),
    cnn: t(
      "Gravity map to column-density prediction",
      "Mapa gravimétrico a densidad integrada",
    ),
    ae: t(
      "Observation compression and reconstruction error",
      "Compresión de observaciones y error de reconstrucción",
    ),
    protocol: t(
      "Realization-disjoint learning protocol",
      "Protocolo con realizaciones disjuntas",
    ),
  };
  const box = (x: number, y: number, w: number, h: number, active = false) => (
    <rect
      x={x}
      y={y}
      width={w}
      height={h}
      rx={6}
      className={active ? "diagram-active" : "diagram-box"}
    />
  );
  const txt = (x: number, y: number, s: string) => (
    <text x={x} y={y}>
      {s}
    </text>
  );
  return (
    <Figure caption={title[kind]}>
      <svg
        className="method-diagram"
        viewBox="0 0 760 270"
        role="img"
        aria-label={title[kind]}
      >
        <title>{title[kind]}</title>
        {kind === "potential" && (
          <>
            <path
              className="diagram-edge"
              d="M30 75H360 M30 230H360 M30 75V230"
            />
            {[60, 110, 160, 210, 260, 310].map((x) => (
              <g key={x}>
                <circle cx={x} cy={60} r={4} fill="var(--color-accent)" />
                <path
                  d={`M${x} 66L170 170 M${x} 66L285 205`}
                  className="diagram-edge"
                  opacity=".4"
                />
              </g>
            ))}
            {box(130, 140, 80, 45, true)}
            {box(250, 185, 65, 45)}
            {txt(40, 35, t("Surface stations: 16 × 16", "Estaciones: 16 × 16"))}
            {txt(140, 169, "mⱼ")}
            {txt(267, 214, "mₖ")}
            {txt(390, 72, "dᵢ = Σⱼ Gᵢⱼ mⱼ")}
            {txt(390, 115, t("G: 256 × 10,752", "G: 256 × 10.752"))}
            {txt(
              390,
              155,
              t("Cells: 80 × 80 × 70 m", "Celdas: 80 × 80 × 70 m"),
            )}
            {txt(
              390,
              195,
              t(
                "Vector model: 3 components/cell",
                "Vector: 3 componentes/celda",
              ),
            )}
            {txt(
              40,
              258,
              t(
                "Deeper prisms affect a broader surface footprint.",
                "Prismas profundos afectan un área superficial más amplia.",
              ),
            )}
          </>
        )}
        {kind === "mt" && (
          <>
            {[0, 1, 2].map((j) => (
              <g key={j}>
                {box(30, 30 + j * 65, 310, 60, j === 1)}
                {txt(
                  48,
                  65 + j * 65,
                  `ρ${j + 1}${j < 2 ? `, h${j + 1}` : t(" · halfspace", " · semiespacio")}`,
                )}
              </g>
            ))}
            <path
              d="M370 215V60l-7 12m7-12l7 12"
              className="diagram-highlight"
            />
            {txt(403, 55, t("Surface: Z₁(f)", "Superficie: Z₁(f)"))}
            {txt(403, 103, t("Layer 2: Z₂ ← Z₃", "Capa 2: Z₂ ← Z₃"))}
            {txt(403, 151, "kⱼ = √(iωμ₀/ρⱼ)")}
            {txt(403, 199, "Z₃ = √(iωμ₀ρ₃)")}
            {txt(
              40,
              258,
              t(
                "Each frequency samples the full layered column.",
                "Cada frecuencia muestrea toda la columna estratificada.",
              ),
            )}
          </>
        )}
        {kind === "seismic" && (
          <>
            {box(30, 30, 390, 200)}
            <path d="M30 120H220V155H420" className="diagram-highlight" />
            {[70, 205, 335].map((x) => (
              <g key={x}>
                <circle cx={x} cy={60} r={5} fill="var(--color-bad)" />
                <path
                  d={`M${x} 68Q${x - 40} 120 ${x + 30} 180`}
                  className="diagram-edge"
                />
              </g>
            ))}
            {Array.from({ length: 15 }, (_, i) => (
              <rect
                key={i}
                x={48 + i * 24}
                y={78}
                width={5}
                height={5}
                fill="var(--color-accent)"
              />
            ))}
            {txt(45, 210, "128 × 96 · Δx = Δz = 12.5 m")}
            {txt(
              450,
              57,
              t("3 sources / 40 receivers", "3 fuentes / 40 receptores"),
            )}
            {txt(
              450,
              105,
              t("Forward: velocity → traces", "Directo: velocidad → trazas"),
            )}
            {txt(
              450,
              153,
              t("Residual: predicted − observed", "Residuo: predicción − dato"),
            )}
            {txt(
              450,
              201,
              t("Backward: loss → gradient", "Inverso: pérdida → gradiente"),
            )}
            {txt(
              40,
              258,
              t(
                "Pressure replay and velocity updates are different quantities.",
                "Presión reproducida y velocidad iterada son cantidades distintas.",
              ),
            )}
          </>
        )}
        {kind === "joint" && (
          <>
            {box(30, 35, 320, 160)}
            {box(400, 35, 320, 160)}
            <path
              d="M70 170L255 65M95 180L280 75"
              className="diagram-highlight"
            />
            <path d="M450 175L665 70" className="diagram-highlight" />
            <path d="M450 70L665 175" className="diagram-warning" />
            {txt(
              65,
              220,
              t("Parallel gradients: c = 0", "Gradientes paralelos: c = 0"),
            )}
            {txt(
              423,
              220,
              t("Crossing gradients: c ≠ 0", "Gradientes cruzados: c ≠ 0"),
            )}
            {txt(
              40,
              258,
              t(
                "Zero gradient also gives c = 0; data fit is still required.",
                "Gradiente nulo también da c = 0; sigue siendo necesario ajustar datos.",
              ),
            )}
          </>
        )}
        {(kind === "cnn" || kind === "ae") && (
          <>
            {box(25, 65, 145, 115)}
            {box(205, 80, 160, 85, true)}
            {box(400, 95, 125, 55)}
            {box(560, 65, 175, 115, true)}
            <path
              d="M170 122H205 M365 122H400 M525 122H560"
              className="diagram-edge"
            />
            {txt(38, 100, "16 × 16")}
            {txt(38, 130, t("gravity map", "mapa de gravedad"))}
            {txt(220, 110, kind === "cnn" ? "Conv 16 → 24" : "Dense 256 → 64")}
            {txt(220, 142, kind === "cnn" ? "Pool 4 × 4" : "GELU")}
            {txt(418, 128, kind === "cnn" ? "384 → 96" : "latent 12")}
            {txt(575, 102, kind === "cnn" ? "24 × 28" : "16 × 16")}
            {txt(
              575,
              133,
              kind === "cnn"
                ? t("column density", "densidad integrada")
                : t("reconstruction", "reconstrucción"),
            )}
            {txt(
              40,
              235,
              kind === "cnn"
                ? t(
                    "Target: Σ density × layer thickness; no depth coordinate.",
                    "Objetivo: Σ densidad × espesor; sin coordenada de profundidad.",
                  )
                : t(
                    "Score: mean squared observation error, compared with calibration Q₀.₉₉.",
                    "Puntaje: error cuadrático de observaciones, comparado con Q₀,₉₉ de calibración.",
                  ),
            )}
          </>
        )}
        {kind === "protocol" && (
          <>
            {box(25, 25, 710, 45)}
            {txt(
              45,
              54,
              t(
                "Split complete geological realizations before fitting or normalization",
                "Separar realizaciones geológicas antes de ajustar o normalizar",
              ),
            )}
            {[
              ["800", t("Training", "Entrenamiento")],
              ["160", t("Validation", "Validación")],
              ["160", t("Test", "Prueba")],
            ].map(([n, s], i) => (
              <g key={s}>
                {box(30 + i * 245, 105, 215, 75, i === 0)}
                {txt(50 + i * 245, 135, s)}
                {txt(50 + i * 245, 162, n)}
              </g>
            ))}
            <path
              d="M138 70V105 M383 70V105 M628 70V105"
              className="diagram-edge"
            />
            {txt(
              45,
              220,
              t(
                "Forbidden: test statistics → normalization or checkpoint selection",
                "Prohibido: estadísticas de prueba → normalización o selección",
              ),
            )}
            <path
              d="M40 228L710 209 M40 209L710 228"
              className="diagram-warning"
            />
          </>
        )}
      </svg>
    </Figure>
  );
}
