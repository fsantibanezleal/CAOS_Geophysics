import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import {
  AppShell,
  Landing,
  applyTheme,
  readTheme,
  CitationsProvider,
  useLangStore,
  type ShellConfig,
} from "@fasl-work/caos-app-shell";
import { Activity } from "lucide-react";
import "@fasl-work/caos-app-shell/styles.css";
import "@fasl-work/caos-app-shell/chart.css";
import "./styles.css";
import { CITATIONS } from "./data/citations";
import { architecture } from "./architecture";
import { PRODUCT_ROUTES } from "./lib/routes";
import { deploymentMode, routerBasename } from "./lib/deployment";

const Workbench = lazy(() => import("./pages/Workbench"));
const Intro = lazy(() => import("./pages/Research").then(module => ({ default: module.Introduction })));
const Methodology = lazy(() => import("./pages/Research").then(module => ({ default: module.Methodology })));
const Implementation = lazy(() => import("./pages/Research").then(module => ({ default: module.Implementation })));
const Experiments = lazy(() => import("./pages/Research").then(module => ({ default: module.Experiments })));
const Benchmark = lazy(() => import("./pages/Research").then(module => ({ default: module.Benchmark })));

function RouteLoading() {
  const lang = useLangStore(state => state.lang);
  return (
    <div className="load-state" data-state="loading" role="status" aria-live="polite">
      <Activity size={18} aria-hidden="true" />
      {lang === "es" ? "Cargando la vista geofísica…" : "Loading geophysics view…"}
    </div>
  );
}

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
  version: "0.04.002",
  visibility: "public",
  contain: true,
  license: {
    en: "Apache code license · CC BY content license",
    es: "Licencia Apache para código · licencia CC BY para contenido",
  },
  architecture,
  fixedRoutes: ["/app"],
  footer: {
    attribution: {
      en: "Developed by Felipe Santibáñez-Leal",
      es: "Desarrollado por Felipe Santibáñez-Leal",
    },
    license: {
      en: "Apache code license · CC BY content license",
      es: "Licencia Apache para código · licencia CC BY para contenido",
    },
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter basename={routerBasename(deploymentMode, window.location.pathname)}>
      <CitationsProvider items={CITATIONS}>
        <AppShell config={config}>
          <Suspense fallback={<RouteLoading />}>
            <Routes>
              <Route path="/" element={<Landing />} />
              {PRODUCT_ROUTES.map(({ id, path }) => (
                <Route key={id} path={path} element={pageElements[id as keyof typeof pageElements]} />
              ))}
              <Route path="*" element={<Landing />} />
            </Routes>
          </Suspense>
        </AppShell>
      </CitationsProvider>
    </BrowserRouter>
  </StrictMode>,
);
