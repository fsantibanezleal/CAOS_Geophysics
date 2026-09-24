import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { color, extent, format, type Run } from "../science";
import { useShellLang } from "@fasl-work/caos-app-shell";

export function EarthScene({
  run,
  values,
  opacity,
  cut,
  showSurvey,
  angle,
  speed,
  playing,
  reset,
  label,
  onCell,
}: {
  run: Run;
  values: number[];
  opacity: number;
  cut: number;
  showSurvey: boolean;
  angle: number;
  speed: number;
  playing: boolean;
  reset: number;
  label: string;
  onCell?: (i: number) => void;
}) {
  const es = useShellLang() === "es";
  const host = useRef<HTMLDivElement>(null);
  const animate = useRef({ playing, speed });
  animate.current = { playing, speed };
  const [readout, setReadout] = useState("");
  const [error, setError] = useState("");
  const pose = useRef<{
    position: THREE.Vector3;
    target: THREE.Vector3;
  } | null>(null);
  const resetRef = useRef(reset);
  const angleRef = useRef(angle);
  useEffect(() => {
    const container = host.current;
    if (!container || !run.grid?.centers || !run.survey) return;
    const scene = new THREE.Scene();
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    } catch {
      setError(
        "WebGL is unavailable. Use the section view to inspect the same model.",
      );
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);
    const camera = new THREE.PerspectiveCamera(34, 1, 0.01, 50);
    camera.position.set(3, 1.9, 3.3);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, -0.45, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.12;
    controls.minDistance = 1.8;
    controls.maxDistance = 9;
    controls.maxPolarAngle = Math.PI * 0.78;
    const isReset = reset !== resetRef.current;
    if (pose.current && !isReset) {
      camera.position.copy(pose.current.position);
      controls.target.copy(pose.current.target);
    }
    resetRef.current = reset;
    if (angle !== angleRef.current && !isReset) {
      const delta = ((angle - angleRef.current) * Math.PI) / 180;
      const offset = camera.position
        .clone()
        .sub(controls.target)
        .applyAxisAngle(new THREE.Vector3(0, 1, 0), delta);
      camera.position.copy(controls.target).add(offset);
    }
    angleRef.current = angle;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x83909b, 2.0));
    const sun = new THREE.DirectionalLight(0xffffff, 2);
    sun.position.set(-3, 5, 4);
    scene.add(sun);
    const bounds = extent(values);
    const max = Math.max(...values.map(Math.abs));
    const diverging = bounds[0] < -max * 0.1;
    const palette = diverging ? "field" : "earth";
    const range: [number, number] = diverging ? [-max, max] : [0, max];
    const indices: number[] = [];
    for (let i = 0; i < values.length; i++) {
      if (Math.abs(values[i]) > max * 0.1 && run.grid.centers[i][1] <= cut)
        indices.push(i);
    }
    const spacing = run.grid.spacing;
    const geometry = new THREE.BoxGeometry(
      (spacing[0] / 1000) * 0.97,
      (spacing[2] / 1000) * 0.97,
      (spacing[1] / 1000) * 0.97,
    );
    const material = new THREE.MeshStandardMaterial({
      roughness: 0.78,
      metalness: 0,
      transparent: opacity < 1,
      opacity,
      depthWrite: opacity > 0.65,
    });
    const voxels = new THREE.InstancedMesh(geometry, material, indices.length);
    const transform = new THREE.Matrix4();
    indices.forEach((i, j) => {
      const p = run.grid!.centers![i];
      transform.makeTranslation(p[0] / 1000, p[2] / 1000, p[1] / 1000);
      voxels.setMatrixAt(j, transform);
      voxels.setColorAt(j, new THREE.Color(color(values[i], range, palette)));
    });
    voxels.instanceMatrix.needsUpdate = true;
    scene.add(voxels);
    const box = new THREE.BoxGeometry(2.24, 1.12, 1.92);
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(box),
      new THREE.LineBasicMaterial({
        color: 0x9caaa9,
        transparent: true,
        opacity: 0.42,
      }),
    );
    edges.position.y = -0.56;
    scene.add(edges);
    const grid = new THREE.GridHelper(2.24, 14, 0x879392, 0xb8beb7);
    grid.position.y = -1.125;
    grid.scale.z = 1.92 / 2.24;
    scene.add(grid);
    const surveyValues = run.survey.observed;
    const observedMax = Math.max(...surveyValues.map(Math.abs));
    if (showSurvey) {
      const geom = new THREE.PlaneGeometry(0.132, 0.12);
      geom.rotateX(-Math.PI / 2);
      const mat = new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0.32,
        side: THREE.DoubleSide,
      });
      const plane = new THREE.InstancedMesh(geom, mat, 256);
      run.survey.locations.forEach((p, i) => {
        transform.makeTranslation(
          p[0] / 1000,
          p[2] / 1000 + 0.035,
          p[1] / 1000,
        );
        plane.setMatrixAt(i, transform);
        plane.setColorAt(
          i,
          new THREE.Color(
            color(surveyValues[i], [-observedMax, observedMax], "field"),
          ),
        );
      });
      scene.add(plane);
      const positions = run.survey.locations
        .filter((_, i) => run.survey!.active[i])
        .flatMap((p) => [p[0] / 1000, p[2] / 1000 + 0.045, p[1] / 1000]);
      const points = new THREE.BufferGeometry();
      points.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(positions, 3),
      );
      scene.add(
        new THREE.Points(
          points,
          new THREE.PointsMaterial({ color: 0x263b4c, size: 0.017 }),
        ),
      );
    }
    const labels: THREE.Sprite[] = [];
    const sprite = (text: string, p: THREE.Vector3) => {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 80;
      const ctx = canvas.getContext("2d")!;
      ctx.font = "28px system-ui";
      ctx.fillStyle = getComputedStyle(document.documentElement)
        .getPropertyValue("--color-fg")
        .trim();
      ctx.textAlign = "center";
      ctx.fillText(text, 256, 48);
      const texture = new THREE.CanvasTexture(canvas);
      const sp = new THREE.Sprite(
        new THREE.SpriteMaterial({ map: texture, depthTest: false }),
      );
      sp.scale.set(0.9, 0.14, 1);
      sp.position.copy(p);
      scene.add(sp);
      labels.push(sp);
    };
    sprite(es ? "Este · m" : "Easting · m", new THREE.Vector3(0, -1.27, 1.1));
    sprite(
      es ? "Norte · m" : "Northing · m",
      new THREE.Vector3(-1.35, -1.2, 0),
    );
    sprite("0", new THREE.Vector3(-1.22, 0, 1));
    sprite("−1,120 m", new THREE.Vector3(-1.28, -1.09, 1));
    sprite("2,240 m", new THREE.Vector3(0.95, -1.18, 1.13));
    const theme = () => {
      const css = getComputedStyle(document.documentElement);
      scene.background = new THREE.Color(
        css.getPropertyValue("--scene-bg").trim() || "#edf0eb",
      );
    };
    theme();
    const themeObserver = new MutationObserver(theme);
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    const resize = new ResizeObserver(() => {
      const { width, height } = container.getBoundingClientRect();
      if (width && height) {
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.zoom = Math.min(1, camera.aspect / 1.25);
        camera.updateProjectionMatrix();
      }
    });
    resize.observe(container);
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    let picked: number | undefined;
    const move = (event: PointerEvent) => {
      const r = renderer.domElement.getBoundingClientRect();
      pointer.set(
        ((event.clientX - r.left) / r.width) * 2 - 1,
        (-(event.clientY - r.top) / r.height) * 2 + 1,
      );
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObject(voxels)[0];
      if (hit?.instanceId !== undefined) {
        picked = indices[hit.instanceId];
        const p = run.grid!.centers![picked];
        setReadout(
          `E ${p[0]} · N ${p[1]} · depth ${-p[2]} m | ${format(values[picked])} ${run.units}`,
        );
      } else {
        picked = undefined;
        setReadout("");
      }
    };
    const click = () => {
      if (picked !== undefined) onCell?.(picked);
    };
    renderer.domElement.addEventListener("pointermove", move);
    renderer.domElement.addEventListener("click", click);
    let frame = 0;
    let previous = performance.now();
    const render = (time: number) => {
      const dt = Math.min((time - previous) / 1000, 0.05);
      previous = time;
      controls.autoRotate = animate.current.playing;
      controls.autoRotateSpeed = animate.current.speed / 6;
      controls.update(dt);
      renderer.render(scene, camera);
      frame = requestAnimationFrame(render);
    };
    frame = requestAnimationFrame(render);
    return () => {
      pose.current = {
        position: camera.position.clone(),
        target: controls.target.clone(),
      };
      cancelAnimationFrame(frame);
      resize.disconnect();
      themeObserver.disconnect();
      controls.dispose();
      scene.traverse((o) => {
        if (
          o instanceof THREE.Mesh ||
          o instanceof THREE.LineSegments ||
          o instanceof THREE.Points
        ) {
          o.geometry.dispose();
          const mats = Array.isArray(o.material) ? o.material : [o.material];
          mats.forEach((m) => m.dispose());
        }
        if (o instanceof THREE.Sprite) {
          o.material.map?.dispose();
          o.material.dispose();
        }
      });
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, [run, values, opacity, cut, showSurvey, angle, reset, onCell, es]);
  return (
    <div
      className="earth-scene"
      ref={host}
      role="img"
      aria-label={`${label}: three-dimensional subsurface model and survey`}
    >
      <div className="scene-label">
        <span className="small-caps">3D / {label}</span>
        <strong>{es ? run.name_es : run.name}</strong>
      </div>
      <div className="scene-instructions">
        {es
          ? "Arrastre para orbitar · Rueda para zoom · Seleccione un vóxel"
          : "Drag to orbit · Scroll to zoom · Select a voxel"}
      </div>
      <output className="scene-readout">
        {error ||
          readout ||
          `${run.grid?.shape.join(" × ")} cells · ${run.units}`}
      </output>
      <div className="scene-compass">
        <b>N</b>
        <span>↑</span>
      </div>
    </div>
  );
}
