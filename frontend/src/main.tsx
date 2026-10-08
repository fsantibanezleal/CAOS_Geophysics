import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import {
  AppShell,
  applyTheme,
  readTheme,
  CitationsProvider,
  useLangStore,
  type ShellConfig,
} from "@fasl-work/caos-app-shell";
import { Activity } from "lucide-react";
import "@fasl-work/caos-app-shell/styles.css";
import "./styles.css";
import { CITATIONS } from "./data/citations";
import { architecture } from "./architecture";
import {
  Workbench,
  Intro,
  Methodology,
  Implementation,
  Experiments,
  Benchmark,
} from "./pages";
import { PRODUCT_ROUTES } from "./lib/routes";
import { deploymentMode, routerBasename } from "./lib/deployment";

applyTheme(readTheme());
if (typeof localStorage !== "undefined" && !localStorage.getItem("caos.lang"))
  useLangStore.getState().setLang("en");

const pageElements = {
  app: <Workbench />,
  introduction: <Intro />,
  methodology: <Methodology />,
  implementation: <Implementation />,
  experiments: <Experiments />,
  benchmark: <Benchmark />,
};

const config: ShellConfig = {
  product: {
    name: "Inverse Earth Studio",
    mark: <Activity size={18} aria-hidden="true" />,
  },
  routes: PRODUCT_ROUTES.map(({ path, en, es }) => ({ path, en, es })),
  links: { github: "https://github.com/fsantibanezleal/CAOS_Geophysics" },
  version: "0.04.001",
  visibility: "public",
  license: {
    en: "Apache-2.0 code and CC-BY-4.0 content",
    es: "Código Apache-2.0 y contenido CC-BY-4.0",
  },
  architecture,
  contain: true,
  fixedRoutes: ["/"],
  footer: {
    attribution: {
      en: "Developed by Felipe Santibáñez-Leal",
      es: "Desarrollado por Felipe Santibáñez-Leal",
    },
    provenance: {
      en: "Geophysical observations and method evidence.",
      es: "Observaciones geofísicas y evidencia de métodos.",
    },
    license: {
      en: "Apache-2.0 code and CC-BY-4.0 content",
      es: "Código Apache-2.0 y contenido CC-BY-4.0",
    },
    disclaimer: {
      en: "Inspect source, units and method-specific limitations.",
      es: "Revise fuente, unidades y límites específicos del método.",
    },
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={routerBasename(deploymentMode, window.location.pathname)}>
      <CitationsProvider items={CITATIONS}>
        <AppShell config={config}>
          <Routes>
            {PRODUCT_ROUTES.map(({ id, path }) => (
              <Route key={id} path={path} element={pageElements[id as keyof typeof pageElements]} />
            ))}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppShell>
      </CitationsProvider>
    </BrowserRouter>
  </StrictMode>,
);
