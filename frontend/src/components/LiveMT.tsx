import { useMemo, useState } from "react";
import { useShellLang } from "@fasl-work/caos-app-shell";
import { mtForward } from "../mt";
import { LayerColumn, Plot } from "./ScientificPlots";
export function LiveMT() {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => (es ? b : a);
  const [rho, setRho] = useState([300, 15, 900]);
  const [h, setH] = useState([300, 550]);
  const [minimum, setMinimum] = useState(-3);
  const f = useMemo(
    () =>
      Array.from(
        { length: 64 },
        (_, i) => 10 ** (minimum + (i * (3 - minimum)) / 63),
      ),
    [minimum],
  );
  const result = useMemo(() => mtForward(rho, h, f), [rho, h, f]);
  const reference = useMemo(
    () => mtForward([300, 15, 900], [300, 550], f),
    [f],
  );
  const [error, setError] = useState("");
  return (
    <section className="method-article">
      <h2>
        {t(
          "Layered-earth MT forward response",
          "Respuesta directa MT de un medio estratificado",
        )}
      </h2>
      <p>
        {t(
          "Change a layer and the browser recomputes the complex impedance recursion immediately. The dashed curve is the fixed reference aquifer; solid curves represent the specified model. This is forward modelling, not an inversion of observed field data.",
          "Cambie una capa y el navegador recalcula la recursión de impedancia. La curva segmentada es el acuífero de referencia; las curvas continuas representan el modelo especificado. Es modelación directa, no inversión de datos de campo.",
        )}
      </p>
      <div className="mt-view">
        <div>
          <LayerColumn
            rho={rho}
            thickness={h}
            title={t("Resistivity model", "Modelo de resistividad")}
          />
          {rho.map((value, i) => (
            <label key={i} className="range-control">
              <span>
                {t("Layer", "Capa")} {i + 1}
                <output>{value.toFixed(1)} Ω m</output>
              </span>
              <input
                aria-label={`${t("Layer", "Capa")} ${i + 1} Ω m`}
                type="range"
                className="range"
                min={0}
                max={4}
                step={0.025}
                value={Math.log10(value)}
                onChange={(e) =>
                  setRho((r) =>
                    r.map((v, j) =>
                      j === i ? 10 ** Number(e.target.value) : v,
                    ),
                  )
                }
              />
            </label>
          ))}
          {h.map((value, i) => (
            <label key={i} className="range-control">
              <span>
                h{i + 1}
                <output>{value} m</output>
              </span>
              <input
                aria-label={`h${i + 1} m`}
                type="range"
                className="range"
                min={10}
                max={2000}
                step={10}
                value={value}
                onChange={(e) =>
                  setH((a) => a.map((v, j) => (j === i ? +e.target.value : v)))
                }
              />
            </label>
          ))}
          <label className="range-control">
            <span>
              {t("Minimum frequency", "Frecuencia mínima")}
              <output>{10 ** minimum} Hz</output>
            </span>
            <input
              aria-label={t("Minimum frequency", "Frecuencia mínima")}
              type="range"
              className="range"
              min={-4}
              max={0}
              value={minimum}
              onChange={(e) => setMinimum(+e.target.value)}
            />
          </label>
        </div>
        <div className="mt-curves">
          <Plot
            title={t("Apparent resistivity", "Resistividad aparente")}
            x={f}
            series={[
              {
                name: t("Reference", "Referencia"),
                values: reference.apparent,
                dashed: true,
              },
              {
                name: t("Specified model", "Modelo especificado"),
                values: result.apparent,
              },
            ]}
            xLabel="Hz"
            yLabel="Ω m"
            logX
            logY
          />
          <Plot
            title={t("Phase", "Fase")}
            x={f}
            series={[
              {
                name: t("Reference", "Referencia"),
                values: reference.phase,
                dashed: true,
              },
              {
                name: t("Specified model", "Modelo especificado"),
                values: result.phase,
              },
            ]}
            xLabel="Hz"
            yLabel="°"
            logX
          />
          <div className="sidebar-actions">
            <button
              className="btn"
              onClick={() => {
                setRho([300, 15, 900]);
                setH([300, 550]);
                setMinimum(-3);
                setError("");
              }}
            >
              {t("Reset model", "Restablecer modelo")}
            </button>
            <button
              className="btn"
              onClick={() => {
                const url = URL.createObjectURL(
                  new Blob(
                    [
                      JSON.stringify({
                        schema: "inverse-earth.mt-input/v2",
                        rho,
                        thickness: h,
                        frequencies: f,
                        ...result,
                      }),
                    ],
                    { type: "application/json" },
                  ),
                );
                const a = document.createElement("a");
                a.href = url;
                a.download = "layered-earth.json";
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              {t("Download model + response", "Descargar modelo y respuesta")}
            </button>
          </div>
          <label className="select-control">
            <span>
              {t(
                "Import your model JSON: rho[] and thickness[] (2–8 layers)",
                "Importar modelo JSON: rho[] y thickness[] (2–8 capas)",
              )}
            </span>
            <input
              type="file"
              accept=".json,application/json"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                try {
                  if (file.size > 100000)
                    throw Error(
                      t("Maximum file size: 100 kB", "Tamaño máximo: 100 kB"),
                    );
                  const m = JSON.parse(await file.text());
                  if (
                    !Array.isArray(m.rho) ||
                    m.rho.length < 2 ||
                    m.rho.length > 8 ||
                    !Array.isArray(m.thickness) ||
                    m.thickness.length !== m.rho.length - 1 ||
                    m.rho.some(
                      (v: unknown) =>
                        typeof v !== "number" ||
                        !Number.isFinite(v) ||
                        v < 1 ||
                        v > 10000,
                    ) ||
                    m.thickness.some(
                      (v: unknown) =>
                        typeof v !== "number" ||
                        !Number.isFinite(v) ||
                        v < 10 ||
                        v > 2000,
                    )
                  )
                    throw Error(
                      t(
                        "Require 2–8 resistivities in [1,10000] Ω m and one fewer thicknesses in [10,2000] m.",
                        "Se requieren 2–8 resistividades [1,10000] Ω m y un espesor menos [10,2000] m.",
                      ),
                    );
                  setRho(m.rho);
                  setH(m.thickness);
                  setError("");
                } catch (err) {
                  setError(String(err));
                }
                e.target.value = "";
              }}
            />
          </label>
          {error && <p role="alert">{error}</p>}
        </div>
      </div>
    </section>
  );
}
