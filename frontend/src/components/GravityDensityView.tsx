import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { PlotCard, Stage } from "@fasl-work/caos-app-shell";
import type { GravityAcceptedFrame } from "../api/gravity-density-contract";

type Cell = { index: number; bounds: number[]; density: number; centre: [number, number, number] };

export type GravityVolumeData = { active_cell_indices: number[]; bounds_m: number[][]; density_kg_m3: number[] | null };

export function densityCells(data: GravityVolumeData): Cell[] {
  if (!data.density_kg_m3) return [];
  if (data.bounds_m.length !== data.density_kg_m3.length
      || data.active_cell_indices.length !== data.bounds_m.length) {
    throw new Error("Gravity active-cell arrays are not aligned");
  }
  if (data.active_cell_indices.some(index => !Number.isSafeInteger(index) || index < 0)
      || new Set(data.active_cell_indices).size !== data.active_cell_indices.length) {
    throw new Error("Gravity active-cell indices must be unique nonnegative integers");
  }
  const cells = data.bounds_m.map((bounds, index) => {
    if (bounds.length !== 6 || bounds.some(value => !Number.isFinite(value)) || !Number.isFinite(data.density_kg_m3![index]))
      throw new Error("Gravity volume contains invalid physical cell bounds or density");
    const [x0, x1, y0, y1, z0, z1] = bounds;
    if (!(x1 > x0 && y1 > y0 && z1 > z0)) throw new Error("Gravity volume cell has nonpositive extent");
    return { index: data.active_cell_indices[index], bounds, density: data.density_kg_m3![index],
      centre: [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2] as [number, number, number] };
  });
  if (cells.length !== data.active_cell_indices.length) throw new Error("Gravity active-cell arrays are not aligned");
  return cells;
}

function diverging(value: number, maximum: number): THREE.Color {
  const t = Math.min(1, Math.abs(value) / (maximum || 1));
  const low = value < 0 ? new THREE.Color("#245f86") : new THREE.Color("#9c452f");
  return new THREE.Color("#eee8d8").lerp(low, 0.22 + 0.78 * t);
}

function VolumeCanvas({ cells, density, densityScale, verticalExaggeration, section, width, height, ariaLabel }: {
  cells: Cell[]; density: number[]; densityScale: number; verticalExaggeration: number; section: number; width: number; height: number; ariaLabel: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const updateScene = useRef<((sectionIndex: number, exaggeration: number) => void) | null>(null);
  const updateDensity = useRef<((density: number[]) => void) | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const element = host.current;
    if (!element || cells.length === 0) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" }); }
    catch { setError("WebGL is unavailable in this browser."); return; }
    setError(null);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(new THREE.Color("#101a20"), 1);
    element.replaceChildren(renderer.domElement);
    renderer.domElement.setAttribute("role", "img");
    renderer.domElement.setAttribute("aria-label", ariaLabel);
    renderer.domElement.tabIndex = 0;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#101a20");
    const camera = new THREE.PerspectiveCamera(38, element.clientWidth / element.clientHeight, 0.01, 1000);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = false;
    controls.listenToKeyEvents(renderer.domElement);
    const group = new THREE.Group(); scene.add(group);
    const min = [0, 1, 2].map(axis => Math.min(...cells.map(cell => cell.bounds[axis * 2])));
    const max = [0, 1, 2].map(axis => Math.max(...cells.map(cell => cell.bounds[axis * 2 + 1])));
    const spans = max.map((value, axis) => value - min[axis]);
    const scale = Math.max(...spans, 1);
    const centre = min.map((value, axis) => (value + max[axis]) / 2);
    const maxDensity = densityScale;
    for (const [cellPosition, cell] of cells.entries()) {
      const [x0, x1, y0, y1, z0, z1] = cell.bounds;
      const geometry = new THREE.BoxGeometry((x1 - x0) / scale, (z1 - z0) / scale,
        (y1 - y0) / scale);
      const material = new THREE.MeshStandardMaterial({ color: diverging(cell.density, maxDensity), roughness: 0.78,
        metalness: 0, transparent: true, opacity: 0.88, side: THREE.DoubleSide });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(((x0 + x1) / 2 - centre[0]) / scale,
        ((z0 + z1) / 2 - centre[2]) / scale,
        -((y0 + y1) / 2 - centre[1]) / scale);
      mesh.userData.cell = cell;
      mesh.userData.cellPosition = cellPosition;
      group.add(mesh);
      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: "#c6d0ce", transparent: true, opacity: 0.42 }));
      edges.position.copy(mesh.position); edges.userData.cell = cell; group.add(edges);
    }
    const extent = Math.max(1, ...spans.map(value => value / scale * verticalExaggeration));
    const grid = new THREE.GridHelper(extent * 1.25, 10, "#63757b", "#37474d");
    grid.position.y = -spans[2] / scale / 2;
    scene.add(grid);
    updateScene.current = (selectedSection, exaggeration) => {
      for (const object of group.children) {
        const cell = object.userData.cell as Cell | undefined;
        if (!cell) continue;
        object.visible = selectedSection < 0 || Math.abs(cell.centre[2] - selectedSection) <= 1e-9 * Math.max(1, Math.abs(selectedSection));
        object.scale.y = exaggeration;
        object.position.y = ((cell.centre[2] - centre[2]) / scale) * exaggeration;
      }
      grid.position.y = -spans[2] / scale * exaggeration / 2;
      render();
    };
    updateDensity.current = density => {
      if (density.length !== cells.length || density.some(value => !Number.isFinite(value))) return;
      group.traverse(object => {
        const cellPosition = object.userData.cellPosition as number | undefined;
        if (cellPosition === undefined || !(object instanceof THREE.Mesh)) return;
        const material = object.material as THREE.MeshStandardMaterial;
        material.color.copy(diverging(density[cellPosition], maxDensity));
      });
      render();
    };
    scene.add(new THREE.HemisphereLight("#e5f0f0", "#233039", 2.1));
    const key = new THREE.DirectionalLight("#fff1d8", 2.5); key.position.set(2, 3, 2); scene.add(key);
    camera.position.set(extent * 1.35, extent * 1.05, extent * 1.35);
    controls.target.set(0, 0, 0); controls.update(); camera.lookAt(0, 0, 0);
    const render = () => renderer.render(scene, camera);
    controls.addEventListener("change", render);
    updateScene.current(section, verticalExaggeration);
    const resize = new ResizeObserver(() => {
      if (!element.clientWidth || !element.clientHeight) return;
      camera.aspect = element.clientWidth / element.clientHeight; camera.updateProjectionMatrix();
      renderer.setSize(element.clientWidth, element.clientHeight, false); render();
    });
    resize.observe(element); render();
    return () => {
      resize.disconnect(); controls.removeEventListener("change", render); controls.dispose();
      updateScene.current = null;
      updateDensity.current = null;
      group.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.LineSegments) {
          object.geometry.dispose();
          const materials = Array.isArray(object.material) ? object.material : [object.material];
          materials.forEach(material => material.dispose());
        }
      });
      grid.geometry.dispose(); (grid.material as THREE.Material).dispose();
      renderer.dispose(); renderer.domElement.remove();
    };
  }, [cells, width, height, ariaLabel]);

  useEffect(() => { updateScene.current?.(section, verticalExaggeration); }, [section, verticalExaggeration]);
  useEffect(() => { updateDensity.current?.(density); }, [density]);

  return <div ref={host} data-testid="gravity-density-volume" aria-label="Orbitable physical density volume" style={{ width, height }}>
    {error && <span role="status">{error}</span>}
  </div>;
}

export function GravityDensityView({ data, frames = [], es = false }: { data: GravityVolumeData; frames?: GravityAcceptedFrame[]; es?: boolean }) {
  const t = (en: string, sp: string) => es ? sp : en;
  const locale = es ? "es-CL" : "en-US";
  const cells = useMemo(() => densityCells(data), [data]);
  const elevations = useMemo(() => [...new Set(cells.map(cell => cell.centre[2]))].sort((a, b) => a - b), [cells]);
  const [sectionIndex, setSectionIndex] = useState(-1);
  const [verticalExaggeration, setVerticalExaggeration] = useState(1);
  const [frameIndex, setFrameIndex] = useState(Math.max(0, frames.length - 1));
  const [playing, setPlaying] = useState(false);
  useEffect(() => { if (!playing || frames.length < 2) return; const timer = window.setInterval(() => setFrameIndex(index => index >= frames.length - 1 ? 0 : index + 1), 650); return () => window.clearInterval(timer); }, [playing, frames.length]);
  useEffect(() => { if (frameIndex >= frames.length) setFrameIndex(Math.max(0, frames.length - 1)); }, [frameIndex, frames.length]);
  const selected = sectionIndex >= 0 && sectionIndex < elevations.length ? elevations[sectionIndex] : -1;
  const currentDensity = frames[frameIndex]?.density_kg_m3 ?? cells.map(cell => cell.density);
  const densityScale = Math.max(1e-12, ...frames.flatMap(frame => frame.density_kg_m3.map(Math.abs)));
  const currentFrame = frames[frameIndex];
  if (!cells.length) return <PlotCard title={t("3D density contrast", "Contraste de densidad 3D")} lane="replay" provenance="real">
    <p className="project-note">{t("This fit has no recorded density frame. No volume is inferred.", "Este ajuste no contiene un marco de densidad registrado. No se infiere ningún volumen.")}</p>
  </PlotCard>;
  const min = [0, 1, 2].map(axis => Math.min(...cells.map(cell => cell.bounds[axis * 2])));
  const max = [0, 1, 2].map(axis => Math.max(...cells.map(cell => cell.bounds[axis * 2 + 1])));
  return <>
  <div className="gravity-density-stage"><PlotCard title={t("Density contrast · physical 3D cells", "Contraste de densidad · celdas físicas 3D")} lane="replay" provenance="real" fill
    note={t("Cell geometry and signed density come from the returned solver arrays. Orbit, slice and vertical exaggeration change display only; they do not change the inverse.", "La geometría de celdas y la densidad con signo provienen de los arreglos devueltos por el solver. Órbita, corte y exageración vertical solo cambian la vista; no modifican la inversión.")}
    actions={<details open><summary>{t("Volume and solver replay", "Volumen y reproducción del solver")}</summary><div className="processing-view-controls">
      {frames.length > 1 && <><div><button className="btn" type="button" onClick={() => setPlaying(value => !value)}>{playing ? t("Pause accepted-state replay", "Pausar reproducción de estados") : t("Play accepted-state replay", "Reproducir estados aceptados")}</button><span> {t("Accepted state", "Estado aceptado")} {frameIndex + 1} / {frames.length}</span></div><label className="select-control"><span>{t("Optimizer accepted state", "Estado aceptado del optimizador")} · {frameIndex + 1} / {frames.length}</span><input className="select" type="range" min="0" max={frames.length - 1} step="1" value={frameIndex} onChange={event => { setPlaying(false); setFrameIndex(Number(event.target.value)); }} /></label><p className="project-note">φ = {currentFrame?.phi_engine.toPrecision(6)} · normalized KKT = {currentFrame?.kkt_normalized.toPrecision(4)} · {t("recorded native accepted iterate; display playback only", "iteración aceptada nativa registrada; solo reproducción visual")}</p></>}
      <label className="select-control"><span>{t("Elevation slice [m]", "Corte de elevación [m]")}</span><select className="select" value={sectionIndex} onChange={event => setSectionIndex(Number(event.target.value))}>
        <option value={-1}>{t("All active cells", "Todas las celdas activas")}</option>{elevations.map((value, index) => <option value={index} key={value}>{value.toLocaleString(locale)} m</option>)}
      </select></label>
      <label className="select-control"><span>{t("Vertical exaggeration", "Exageración vertical")} · {verticalExaggeration.toFixed(1)}×</span><input className="select" type="range" min="1" max="8" step="0.1" value={verticalExaggeration} onChange={event => setVerticalExaggeration(Number(event.target.value))} /></label>
    </div></details>}>
    <Stage label={t("Physical density volume", "Volumen físico de densidad")}>{({ width, height }) =>
      <VolumeCanvas cells={cells} density={currentDensity} densityScale={densityScale} verticalExaggeration={verticalExaggeration} section={selected} width={width} height={height}
        ariaLabel={t("Orbitable density volume from returned physical cell geometry", "Volumen de densidad orbitable con geometría física de celdas devuelta")} />}</Stage>
  </PlotCard></div>
  <p className="project-note">Easting {min[0].toLocaleString(locale)}–{max[0].toLocaleString(locale)} m · Northing {min[1].toLocaleString(locale)}–{max[1].toLocaleString(locale)} m · elevation {min[2].toLocaleString(locale)}–{max[2].toLocaleString(locale)} m. {t("Focus the volume and use arrow keys to rotate; drag to orbit, scroll to zoom, secondary-drag to pan. Density contrast [kg/m³]: negative blue · zero neutral · positive rust.", "Enfoque el volumen y use las flechas para rotar; arrastre para orbitar, use la rueda para acercar y arrastre secundario para desplazar. Contraste de densidad [kg/m³]: azul negativo · neutro cero · óxido positivo.")}</p>
  </>;
}
