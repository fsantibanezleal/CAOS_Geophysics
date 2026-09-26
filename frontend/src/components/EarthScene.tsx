import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { mergeVertices } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { color, format, type Run } from "../science";
import { useShellLang } from "@fasl-work/caos-app-shell";
import { isosurface } from "../isosurface";

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
  representation = "surface",
  threshold,
  range,
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
  representation?: "surface" | "cells";
  threshold: number;
  range: [number, number];
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
        es
          ? "WebGL no está disponible. La sección muestra el mismo modelo."
          : "WebGL is unavailable. The section view shows the same model.",
      );
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.localClippingEnabled = true;
    container.appendChild(renderer.domElement);
    const camera = new THREE.PerspectiveCamera(34, 1, 0.01, 50);
    camera.position.set(2.65, 1.65, 2.9);
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
    const diverging = range[0] < 0;
    const palette = diverging ? "field" : "earth";
    const indices: number[] = [];
    for (let i = 0; i < values.length; i++) {
      if (
        Math.abs(values[i]) > threshold &&
        run.grid.centers[i][1] <= cut
      )
        indices.push(i);
    }
    const spacing = run.grid.spacing;
    const geometry = new THREE.BoxGeometry(
      spacing[0] / 1000,
      spacing[2] / 1000,
      spacing[1] / 1000,
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
    voxels.visible = representation === "cells";
    scene.add(voxels);
    const surfaces: THREE.Mesh[] = [];
    if (representation === "surface" && threshold > 0)
      for (const sign of [1, -1]) {
        if (!values.some((v) => v * sign > threshold)) continue;
        const rawGeometry = new THREE.BufferGeometry();
        rawGeometry.setAttribute(
          "position",
          new THREE.BufferAttribute(
            isosurface(
              values.map((v) => v * sign),
              run.grid.shape,
              run.grid.origin!,
              spacing,
              threshold,
            ),
            3,
          ),
        );
        const meshGeometry = mergeVertices(rawGeometry, 1e-6);
        rawGeometry.dispose();
        meshGeometry.computeVertexNormals();
        const surface = new THREE.Mesh(
          meshGeometry,
          new THREE.MeshStandardMaterial({
            color: color(sign * threshold, range, palette),
            roughness: 0.65,
            side: THREE.DoubleSide,
            transparent: opacity < 1,
            opacity,
            depthWrite: opacity > 0.65,
            clippingPlanes: [
              new THREE.Plane(new THREE.Vector3(0, 0, -1), cut / 1000),
            ],
          }),
        );
        scene.add(surface);
        surfaces.push(surface);
      }
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
    const grid = new THREE.GridHelper(2.24, 14);
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
      const plane = new THREE.InstancedMesh(
        geom,
        mat,
        run.survey.locations.length,
      );
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
    const labels: {
      sprite: THREE.Sprite;
      canvas: HTMLCanvasElement;
      text: string;
    }[] = [];
    const sprite = (text: string, p: THREE.Vector3) => {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 80;
      const ctx = canvas.getContext("2d")!;
      ctx.font =
        "28px " +
        getComputedStyle(document.documentElement).getPropertyValue(
          "--font-sans",
        );
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
      labels.push({ sprite: sp, canvas, text });
    };
    sprite(es ? "Este · m" : "Easting · m", new THREE.Vector3(0, -1.27, 1.1));
    sprite(
      es ? "Norte · m" : "Northing · m",
      new THREE.Vector3(-1.35, -1.2, 0),
    );
    sprite("0", new THREE.Vector3(-1.22, 0, 1));
    sprite("−1,120 m", new THREE.Vector3(-1.28, -1.09, 1));
    sprite("+1,120 m", new THREE.Vector3(1.12, -1.18, 1.13));
    const theme = () => {
      const css = getComputedStyle(document.documentElement);
      scene.background = new THREE.Color(
        css.getPropertyValue("--color-surface").trim(),
      );
      (edges.material as THREE.LineBasicMaterial).color.set(
        css.getPropertyValue("--color-border").trim(),
      );
      for (const material of Array.isArray(grid.material)
        ? grid.material
        : [grid.material])
        material.color.set(css.getPropertyValue("--color-border").trim());
      scene.traverse((o) => {
        if (o instanceof THREE.Points)
          (o.material as THREE.PointsMaterial).color.set(
            css.getPropertyValue("--color-fg").trim(),
          );
      });
      labels.forEach(({ sprite, canvas, text }) => {
        const ctx = canvas.getContext("2d")!;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = css.getPropertyValue("--color-fg").trim();
        ctx.fillText(text, 256, 48);
        sprite.material.map!.needsUpdate = true;
      });
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
      const hit =
        representation === "cells"
          ? raycaster.intersectObject(voxels)[0]
          : raycaster
              .intersectObjects(surfaces)
              .find((h) => h.point.z <= cut / 1000);
      if (hit) {
        const [nz, ny, nx] = run.grid!.shape;
        const o = run.grid!.origin!;
        const cell = (p: number, axis: number, n: number) =>
          Math.max(
            0,
            Math.min(n - 1, Math.floor((p * 1000 - o[axis]) / spacing[axis])),
          );
        picked =
          representation === "cells"
            ? indices[hit.instanceId!]
            : (cell(hit.point.y, 2, nz) * ny + cell(hit.point.z, 1, ny)) * nx +
              cell(hit.point.x, 0, nx);
        const p = run.grid!.centers![picked];
        setReadout(
          `E ${p[0]} · N ${p[1]} · ${es ? "profundidad" : "depth"} ${-p[2]} m | ${format(values[picked])} ${run.units}`,
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
  }, [
    run,
    values,
    opacity,
    cut,
    showSurvey,
    angle,
    reset,
    onCell,
    es,
    representation,
    threshold,
    range[0],
    range[1],
  ]);
  return (
    <div
      className="earth-scene"
      ref={host}
      role="img"
      aria-label={`${label}: ${es ? "modelo tridimensional y levantamiento" : "three-dimensional subsurface model and survey"}`}
    >
      <div className="scene-label">
        <span className="small-caps">3D / {label}</span>
        <strong>{es ? run.name_es : run.name}</strong>
      </div>
      <div className="scene-instructions">
        {es
          ? "Arrastrar: orbitar · Rueda: zoom · Pulsar: sección"
          : "Drag: orbit · Scroll: zoom · Click: section"}
      </div>
      <output className="scene-readout">
        {error ||
          readout ||
          `${run.grid?.shape.join(" × ")} ${es ? "celdas" : "cells"} · ${run.units}`}
      </output>
    </div>
  );
}
