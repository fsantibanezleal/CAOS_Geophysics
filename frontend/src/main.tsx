import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Route, Routes } from 'react-router';
import { AppShell, applyTheme, readTheme, CitationsProvider, useLangStore, type ShellConfig } from '@fasl-work/caos-app-shell';
import { Activity } from 'lucide-react';
import '@fasl-work/caos-app-shell/styles.css';
import './styles.css';
import { CITATIONS } from './data/citations';
import { architecture } from './architecture';
import { Workbench, Intro, Methodology, Implementation, Experiments, Benchmark } from './pages';

applyTheme(readTheme());
if (typeof localStorage !== 'undefined' && !localStorage.getItem('caos.lang')) useLangStore.getState().setLang('en');

const config: ShellConfig = {
  product: { name: 'Inverse Earth Studio', mark: <Activity size={18} aria-hidden="true" /> },
  routes: [
    { path: '/', en: 'App', es: 'App' },
    { path: '/introduction', en: 'Introduction', es: 'Introducción' },
    { path: '/methodology', en: 'Methodology', es: 'Metodología' },
    { path: '/implementation', en: 'Implementation', es: 'Implementación' },
    { path: '/experiments', en: 'Experiments', es: 'Experimentos' },
    { path: '/benchmark', en: 'Benchmark', es: 'Benchmark' },
  ],
  links: { github: 'https://github.com/fsantibanezleal/CAOS_Geophysics' },
  version: '0.01.000',
  architecture,
  fixedRoutes: ['/'],
  footer: {
    attribution: { en: 'Developed by Felipe Santibáñez-Leal', es: 'Desarrollado por Felipe Santibáñez-Leal' },
    provenance: { en: 'Original seeded synthetic cases; solver-backed engines are documented in the research wiki.', es: 'Casos sintéticos originales y sembrados; los motores con solver están documentados en la wiki de investigación.' },
    license: { en: 'Apache-2.0 code and CC-BY-4.0 content', es: 'Código Apache-2.0 y contenido CC-BY-4.0' },
    disclaimer: { en: 'Research instrument: replayable evidence, not field interpretation advice.', es: 'Instrumento de investigación: evidencia reproducible, no consejo de interpretación de campo.' },
  },
};

const pagesBasePath = typeof window !== 'undefined' && window.location.pathname.startsWith('/CAOS_Geophysics') ? '/CAOS_Geophysics' : '';

createRoot(document.getElementById('root')!).render(<StrictMode><BrowserRouter basename={pagesBasePath}><CitationsProvider items={CITATIONS}><AppShell config={config}><Routes>
  <Route path="/" element={<Workbench />} /><Route path="/introduction" element={<Intro />} /><Route path="/methodology" element={<Methodology />} /><Route path="/implementation" element={<Implementation />} /><Route path="/experiments" element={<Experiments />} /><Route path="/benchmark" element={<Benchmark />} /><Route path="*" element={<Workbench />} />
</Routes></AppShell></CitationsProvider></BrowserRouter></StrictMode>);
