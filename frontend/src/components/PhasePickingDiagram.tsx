import { Figure, useShellLang } from "@fasl-work/caos-app-shell";
import type { PickerId } from "../data/phase-picking";

/** Original method schematics. No waveform, score curve or pick shown here is a result. */
export function PhasePickingDiagram({ method }: { method: PickerId }) {
  const es = useShellLang() === "es";
  const t = (en: string, sp: string) => (es ? sp : en);
  const classical = method === "m08";
  const title = classical
    ? t("M08 signal-to-onset and phase-association schematic", "M08: esquema de señal, inicio y asociación de fase")
    : t("M13 PhaseNet-family encoder-decoder schematic", "M13: esquema codificador-decodificador tipo PhaseNet");
  const caption = classical
    ? t("Conceptual sequence, not a measured trace or an executed pick. Windows use seconds and the recorded sample rate.", "Secuencia conceptual, no traza medida ni marca ejecutada. Las ventanas usan segundos y frecuencia registrada.")
    : t("Reference architecture only, not a trained checkpoint or a probability result from this product.", "Sólo arquitectura de referencia, no checkpoint entrenado ni probabilidad producida aquí.");
  const box = (x: number, y: number, width: number, height: number, active = false) => (
    <rect x={x} y={y} width={width} height={height} rx={8} className={active ? "diagram-active" : "diagram-box"} />
  );
  const label = (x: number, y: number, first: string, second: string) => (
    <text x={x} y={y} textAnchor="middle" style={{ fontSize: 17 }}>
      <tspan x={x}>{first}</tspan>
      <tspan x={x} dy="20">{second}</tspan>
    </text>
  );
  return (
    <Figure caption={caption}>
      <svg className="method-diagram" viewBox="0 0 480 340" role="img" aria-label={title}>
        <title>{title}</title>
        {classical ? (
          <>
            {box(20, 35, 205, 70)}
            {label(122, 63, t("3 channels · counts", "3 canales · conteos"), t("UTC + fₛ (Hz)", "UTC + fₛ (Hz)"))}
            {box(255, 35, 205, 70)}
            {label(357, 63, t("StationXML epoch", "Época StationXML"), t("QC / optional m/s", "QC / m/s opcional"))}
            <path className="diagram-edge" d="M225 70H255 M357 105V122H122V145" />
            {box(20, 145, 205, 82, true)}
            {label(122, 173, t("STA/LTA energy", "Energía STA/LTA"), t("Tₛ, Tₗ (s) → samples", "Tₛ, Tₗ (s) → muestras"))}
            <path className="diagram-highlight" d="M52 210H105 M52 207V213 M105 207V213" />
            <path className="diagram-edge" d="M52 217H185 M52 214V220 M185 214V220 M225 186H255" />
            {box(255, 145, 205, 82)}
            {label(357, 173, t("Onset ≠ P/S class", "Inicio ≠ clase P/S"), t("window + 3C", "ventana + 3C"))}
            <path className="diagram-edge" d="M357 227V260" />
            {box(20, 260, 440, 60, true)}
            {label(240, 284, t("UTC P/S pick or unresolved", "Marca UTC P/S o no resuelta"), t("compare analyst time (s)", "comparar con analista (s)"))}
          </>
        ) : (
          <>
            {box(20, 35, 440, 72)}
            {label(240, 63, t("Z / N / E · 3-component window", "Z / N / E · ventana de 3 canales"), t("100 Hz reference; standardized, unitless", "Referencia 100 Hz; normalizada, sin unidad"))}
            <path className="diagram-edge" d="M117 107V145" />
            {box(20, 145, 195, 82)}
            {label(117, 173, t("1D encoder", "Codificador 1D"), t("4 ↓ stages · context", "4 etapas ↓ · contexto"))}
            {box(265, 145, 195, 82)}
            {label(362, 173, t("1D decoder", "Decodificador 1D"), t("4 ↑ stages · detail", "4 etapas ↑ · detalle"))}
            <path className="diagram-edge" d="M215 186H265 M362 227V260" />
            <path className="diagram-highlight" d="M96 145V136H385V145" />
            <text x="240" y="122" textAnchor="middle" style={{ fontSize: 16 }}>{t("skip connections", "conexiones de salto")}</text>
            {box(20, 260, 440, 60, true)}
            {label(240, 284, t("Softmax · noise / P / S", "Softmax · fondo / P / S"), t("peak or abstain; no local result", "máximo o abstención; sin resultado local"))}
          </>
        )}
      </svg>
    </Figure>
  );
}
