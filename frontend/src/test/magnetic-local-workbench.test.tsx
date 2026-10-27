import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { MagneticLocalWorkbench } from "../components/MagneticLocalWorkbench";

describe("public M03 browser-local workbench", () => {
  it.each([false, true])("declares source/frame/mapping/settings and scientific limits in locale (Spanish=%s)", es => {
    const html = renderToStaticMarkup(createElement(MagneticLocalWorkbench, { es, onCurated: vi.fn() }));
    expect(html).toContain(es ? "CSV local" : "Local CSV file");
    expect(html).toContain(es ? "Sistema de referencia de coordenadas proyectadas" : "Projected coordinate reference system");
    expect(html).toContain(es ? "Fracción retenida por líneas completas" : "Whole-line holdout fraction");
    expect(html).toContain(es ? "permanecen en esta pestaña" : "stay in this browser tab");
    expect(html).toContain(es ? "nunca se cargan al servidor" : "never uploaded");
    expect(html).toContain(es ? "No aplica corrección diurna" : "It applies no diurnal");
    expect(html).toContain(es ? "una grilla Delaunay lineal" : "piecewise-linear Delaunay grid");
    expect(html).not.toContain("font-family");
    expect((html.match(/<aside\b/g) ?? [])).toHaveLength(1);
  });
});
