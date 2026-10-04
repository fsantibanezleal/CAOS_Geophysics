"""M01 course gates and (after test-first approval) an owned record producer.

Existing science is imported, never replaced. All controls are authored, not
field observations. Source assertions do not certify product/browser QA.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from importlib.metadata import version
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import harmonica as hm
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from gravity_processing import GravityContractError, digest, normal_gravity, process_survey
from gravity_station_adapter import run_station_corrections
from gravity_transform_controls import control_request, prism_integral
from gravity_transforms import admit, export_bundle, fit_layer, read_request, replay_grid, transform_survey

COURSE = ROOT / "docs/methods/gravity-processing/scientific-course"
FEATURE = ROOT / "docs/design/features/m01-scientific-course"
WEB = ROOT / "data/derived/m01-scientific-course"
INDEX = ROOT / "frontend/src/data/m01-course-record-index.json"
PINS = {
    "gravity_processing.py": "7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321",
    "gravity_station_adapter.py": "b770b16ef87e83dd92f65a90472145ef93a525a9cedf7f55ee3e6f20f8a10cf8",
    "gravity_transforms.py": "d11d0f207c89c308c9f8711da2a31b84b8adaeb0c12597a5ecc89ce527fdecf0",
    "gravity_transform_controls.py": "5ed27d94f55adbfbfabb7db7371affacd42b1d0bb1887ed2322fc36df077afc9",
    "gravity_transform_figures.py": "4a529f2f19bce53ea80d14c007a43d65f99cbd707ad49e2e9bb3cfbf3c96a273",
}
ENGINES = {"boule": "0.5.0", "harmonica": "0.7.0", "numpy": "2.2.6",
           "scipy": "1.15.2", "verde": "1.9.0", "scikit-learn": "1.9.1",
           "matplotlib": "3.10.8"}
ROLES = {
    "request": "request.json", "result": "result.json", "export_receipt": "receipt.json",
    "map_light": "maps-light.svg", "map_dark": "maps-dark.svg",
    "diagnostics_light": "diagnostics-light.svg", "diagnostics_dark": "diagnostics-dark.svg",
    "map_light_png": "maps-light.png", "map_dark_png": "maps-dark.png",
    "diagnostics_light_png": "diagnostics-light.png", "diagnostics_dark_png": "diagnostics-dark.png",
}
IDS = tuple(f"prism-case-{i}" for i in range(3))
CHAPTERS = ("01_quantity-and-reference", "02_plate-and-terrain",
            "03_uncertainty-and-covariance", "04_equivalent-layer",
            "05_spatial-validation", "06_continuation-and-limits")
G = 6.67430e-11
C = 2 * math.pi * G * 1e5
OWNED_RUN_ROOT = ROOT / "data/raw/gravity-m01-transforms"
INDEX_KEYS = {"schema_version", "scenario_id", "label_kind", "request_sha256", "result_sha256",
              "source_pins", "runtime", "artifacts"}
RESULT_KEYS = {"schema_version", "original_correction_result", "geometry", "config", "model",
               "selection", "split", "stations", "evaluation", "axes", "grids", "condition",
               "nonuniqueness", "uncertainty", "resolution", "provenance"}


def require(condition):
    if not condition:
        raise ValueError("Course record does not match the frozen teaching contract.")


def strict_json(raw):
    """Only the owned, byte-bound exporter objects; not a generic upload API."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result)
            result[key] = value
        return result

    def finite(value):
        number = float(value)
        require(math.isfinite(number))
        return number

    def forbidden(_):
        raise ValueError("Nonfinite course JSON is forbidden.")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                       parse_float=finite, parse_constant=forbidden)
    def depth(node, level=0):
        require(level <= 16)
        if type(node) is dict:
            for child in node.values():
                depth(child, level + 1)
        elif type(node) is list:
            for child in node:
                depth(child, level + 1)
    depth(value)
    return value


def bound_bytes(path, expected):
    """Count actual bytes; cap at expected+1, not Content-Length/stat alone."""
    require(type(expected) is int and 0 < expected <= 32 * 1024 * 1024)
    with path.open("rb") as stream:
        raw = stream.read(expected + 1)
    require(len(raw) == expected)
    return raw


def validate_record(item, base, *, expected_result=None):
    """Verify both file-byte and Python scientific domains without rewriting."""
    require(type(item) is dict and set(item) == INDEX_KEYS)
    require(item["schema_version"] == "m01-course-record-1" and item["scenario_id"] in IDS
            and item["label_kind"] == "synthetic_control_replay")
    require(item["source_pins"] == PINS)
    for key in ("request_sha256", "result_sha256"):
        require(type(item[key]) is str and re.fullmatch("[0-9a-f]{64}", item[key]) is not None)
    runtime = item["runtime"]
    require(type(runtime) is dict and set(runtime) == {"python", "python_implementation", "engines"})
    require(type(runtime["python"]) is str and re.fullmatch(r"3\.12\.\d+", runtime["python"]) is not None)
    require(runtime["python_implementation"] == "CPython" and runtime["engines"] == ENGINES)
    entries = item["artifacts"]
    require(type(entries) is list and len(entries) == 11)
    require(all(type(e) is dict and set(e) == {"role", "path", "bytes", "sha256"} for e in entries))
    require({e["role"] for e in entries} == set(ROLES))
    require(len({e["path"] for e in entries}) == 11)
    raw_by_role = {}
    manifest = {}
    directory = base / item["scenario_id"]
    require(not directory.is_symlink() and not directory.is_junction())
    require({p.name for p in directory.iterdir()} == set(ROLES.values()))
    for entry in entries:
        name = ROLES[entry["role"]]
        require(entry["path"] == item["scenario_id"] + "/" + name)
        path = base / entry["path"]
        require(not path.is_symlink() and path.is_file())
        raw = bound_bytes(path, entry["bytes"])
        require(sha256(raw).hexdigest() == entry["sha256"])
        raw_by_role[entry["role"]] = raw
        if name != "receipt.json":
            manifest[name] = {"name": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    request, result, receipt = (strict_json(raw_by_role[r]) for r in ("request", "result", "export_receipt"))
    require(type(receipt) is dict and set(receipt) == {"schema_version", "executed_utc", "request_sha256",
                                                      "result_sha256", "files", "full_method_accepted"})
    require(receipt["schema_version"] == "gravity-transform-export-1" and receipt["full_method_accepted"] is False)
    require(type(receipt["executed_utc"]) is str and receipt["executed_utc"].endswith("+00:00"))
    require(receipt["files"] == [manifest[name] for name in sorted(manifest)])
    require(digest(request) == item["request_sha256"] == receipt["request_sha256"])
    require(digest(result) == item["result_sha256"] == receipt["result_sha256"])
    admit(request)  # complete correction identity, errors, QC and geometry
    require(set(result) == RESULT_KEYS and result["schema_version"] == "gravity-transform-result-1")
    require(result["original_correction_result"] == request["correction_result"])
    require(result["geometry"] == request["geometry"] and result["config"] == request["config"])
    provenance = result["provenance"]
    require(provenance["request_sha256"] == item["request_sha256"])
    require(provenance["engines"] == runtime["engines"] and provenance["python"] == runtime["python"])
    require(provenance["module_sha256"] == PINS["gravity_transforms.py"])
    require(provenance["corrections_reapplied"] is False and provenance["full_method_accepted"] is False
            and provenance["field_gate"] == "open")
    if expected_result is not None:
        require(digest(result) == digest(expected_result))
    return request, result, receipt


def owned_output(output):
    """Operator-selected fresh run below this owner's ignored area only."""
    path = Path(output).absolute()
    require(".." not in path.parts and path != OWNED_RUN_ROOT)
    require(not path.exists() and not path.is_symlink() and not path.is_junction())
    for parent in path.parents:
        require(not parent.is_symlink() and not parent.is_junction())
    path = path.resolve()
    require(path.is_relative_to(OWNED_RUN_ROOT.resolve()))
    return path


def peak_working_set_bytes():
    """Actual process high-water mark, not an incremental/device budget."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("peak", "working", "paged_peak", "paged",
                                                    "nonpaged_peak", "nonpaged", "pagefile", "pagefile_peak")]
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        require(bool(psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)))
        return int(counters.peak)
    import resource
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(maximum if sys.platform == "darwin" else maximum * 1024)


def write_new_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def frontend_runtime_audit():
    """Real TS arithmetic, byte transport and React SSR, NOT product/browser QA.

    Uses the already-approved owned npm installation. No config/package edits,
    lifecycle scripts, browser install, file write or fake scientific result.
    """
    node = shutil.which("node")
    require(node is not None and (ROOT / "frontend/node_modules/vite").is_dir())
    script = r"""
import assert from "node:assert/strict";
import fs from "node:fs";
import { createHash } from "node:crypto";
import { createServer } from "vite";
import react from "@vitejs/plugin-react";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { CitationsProvider, useLangStore, useThemeStore } from "@fasl-work/caos-app-shell";
const started = performance.now(), cpu = process.cpuUsage();
const server = await createServer({configFile:false,root:process.cwd(),plugins:[react()],optimizeDeps:{noDiscovery:true,include:[]},
  server:{middlewareMode:true,hmr:false,watch:null},appType:"custom"});
let checks=0, renders=0, negatives=0;
function near(a,b,tolerance=1e-10) { assert.ok(Math.abs(a-b)<=tolerance); checks++; }
try {
  const d = await server.ssrLoadModule("/src/data/m01-scientific-course.ts");
  const diagram = await server.ssrLoadModule("/src/components/M01CourseDiagram.tsx");
  const exercise = await server.ssrLoadModule("/src/components/M01CourseExercise.tsx");
  const course = await server.ssrLoadModule("/src/components/M01ScientificCourse.tsx");
  near(d.calculateExplanation("E01",{latitude_deg:0}).surface_reference_mgal,978032.53359,1e-5);
  near(d.calculateExplanation("E01",{latitude_deg:90}).surface_reference_mgal,983218.49378,1e-5);
  const plate = d.calculateExplanation("E02",{density_kg_m3:2670,plate_thickness_m:1000});
  near(plate.plate_mgal,111.9687560676875,1e-9); near(plate.subtractive_mgal,-plate.plate_mgal);
  const covariance={a1:1,a2:1,sigma1_mgal:.02,sigma2_mgal:.02,correlation:-1};
  near(d.calculateExplanation("E03",covariance).linear_sd_mgal,0);
  near(d.calculateExplanation("E03",covariance).marginal_sd_upper_bound_mgal,.04);
  near(d.calculateExplanation("E03",{...covariance,correlation:1}).linear_sd_mgal,.04);
  near(d.calculateExplanation("E03",{...covariance,a2:-1,correlation:1}).linear_sd_mgal,0);
  const wave=d.calculateExplanation("E04",{wavelength_m:500,delta_height_m:300,amplitude_mgal:2});
  near(wave.attenuation,0.023054110763106823); near(wave.continued_amplitude_mgal,2*wave.attenuation);
  for (const id of ["E01","E02","E03","E04"]) {
    const values=Object.fromEntries(d.explanationFields[id].map(f=>[f.key,f.initial]));
    for(const f of d.explanationFields[id]) {
      for(const value of [f.min,f.max]) { d.calculateExplanation(id,{...values,[f.key]:value}); checks++; }
      for(const value of [NaN,Infinity,-Infinity,true,"1",null,f.min-1,f.max+1]) {
        assert.throws(()=>d.calculateExplanation(id,{...values,[f.key]:value}),/Invalid explanatory/); negatives++;
      }
      const missing={...values}; delete missing[f.key];
      assert.throws(()=>d.calculateExplanation(id,missing)); negatives++;
    }
    assert.throws(()=>d.calculateExplanation(id,{...values,unknown:1})); negatives++;
  }
  const catalogue=await d.verifiedCatalogue(), loads=[];
  assert.equal(catalogue.length,3);
  const signal=new AbortController().signal;
  function transport(raw,headers={}) {
    let position=0;
    return new Response(new ReadableStream({pull(c){
      if(position===raw.length) { c.close(); return; }
      const end=Math.min(position+8191,raw.length);c.enqueue(raw.subarray(position,end));position=end;
    }}),{headers});
  }
  for(const item of catalogue) {
    const calls=[];
    const fetcher=async(url,init)=>{
      assert.equal(init.cache,"no-store"); assert.equal(init.signal,signal);
      assert.ok(url.startsWith("/data/m01-scientific-course/"+item.scenario_id+"/"));
      calls.push(url);
      return transport(new Uint8Array(fs.readFileSync("../data/derived/m01-scientific-course/"+url.split("/data/m01-scientific-course/")[1])),{"Content-Length":"1"});
    };
    const record=await d.loadCourseRecord(item.scenario_id,signal,fetcher);
    assert.equal(calls.length,3);assert.equal(record.load.parsed_objects,3);
    assert.equal(record.result.geometry.easting_m.length,196);
    loads.push({scenario_id:item.scenario_id,...record.load});
    for(const lang of ["en","es"]) for(const theme of ["light","dark"]) {
      // SSR reads getInitialState, unlike mounted client state. Explicitly
      // select its initial snapshot in this isolated harness only.
      useLangStore.getInitialState().lang=lang;useThemeStore.getInitialState().theme=theme;
      for(const field of ["field","sigma","residual"]) for(let heightIndex=0;heightIndex<3;heightIndex++) {
        const markup=renderToStaticMarkup(React.createElement(diagram.M01CourseDiagram,{result:record.result,heightIndex,field,coverage:true}));
        assert.ok(markup.includes("mGal") && markup.includes("<svg") && markup.includes("null"));
        assert.ok(!markup.includes("NaN") && !markup.includes("undefined"));renders++;
      }
    }
  }
  const entry=catalogue[0].artifacts.find(a=>a.role==="request");
  const raw=new Uint8Array(fs.readFileSync("../data/derived/m01-scientific-course/"+entry.path));
  for(const bytes of [raw.subarray(0,raw.length-1),new Uint8Array([...raw,0]),Uint8Array.from(raw,(v,i)=>i===0?v^1:v)]) {
    await assert.rejects(d.readBoundArtifact(entry,signal,async()=>transport(bytes)));
    negatives++;
  }
  let reached=0;
  for(const change of [{path:"../request.json"},{role:"unknown"},{role:"__proto__",path:"prism-case-0/[object Object]"},
    {bytes:0},{bytes:32*1024*1024+1},{sha256:"bad"},{extra:"unknown"}]) {
    await assert.rejects(d.readBoundArtifact({...entry,...change},signal,async()=>{reached++;return transport(raw);}));
    negatives++;
  }
  assert.equal(reached,0);
  const aborted=new AbortController();aborted.abort();
  await assert.rejects(d.readBoundArtifact(entry,aborted.signal,async()=>{reached++;return transport(raw);}));
  assert.equal(reached,0);negatives++;
  // Supplied request/result corruption never reaches JSON.parse.
  const saved=JSON.parse;let materializations=0;
  JSON.parse=(...args)=>{materializations++;return saved(...args);};
  try { await assert.rejects(d.readBoundArtifact(entry,signal,async()=>transport(new Uint8Array([...raw,0])))); }
  finally { JSON.parse=saved; }
  assert.equal(materializations,0);negatives++;
  for(const lang of ["en","es"]) for(const theme of ["light","dark"]) {
    useLangStore.getInitialState().lang=lang;useThemeStore.getInitialState().theme=theme;
    const wrap=child=>React.createElement(CitationsProvider,{items:d.M01_COURSE_CITATIONS},child);
    for(const lesson of d.lessons) {
      const body=d.lessonBody(lesson,lang==="es"?1:0);
      assert.ok(!/wiki milestone|wiki stage|hito wiki|for this wiki stage/.test(body));
      const text=renderToStaticMarkup(wrap(React.createElement(course.PhysicsText,{text:body,es:lang==="es"})));
      assert.ok(text.includes("katex") && !text.includes("katex-error"));renders++;
      const picture=renderToStaticMarkup(React.createElement(diagram.M01CourseDiagram,{chapter:lesson.id}));
      assert.ok(picture.includes("data:image/svg+xml"));renders++;
    }
    for(const id of ["E01","E02","E03","E04"]) {
      const markup=renderToStaticMarkup(React.createElement(exercise.M01CourseExercise,{exercise:id}));
      assert.ok(markup.includes(lang==="es"?"Aplicar":"Apply"));renders++;
    }
    const article=renderToStaticMarkup(wrap(React.createElement(course.M01ScientificCourse)));
    assert.ok(article.includes("data-m01-course"));renders++;
  }
  const usage=process.cpuUsage(cpu);
  console.log(JSON.stringify({kind:"local_typescript_arithmetic_transport_react_ssr",
    node:process.version,checks,negative_assertions:negatives,ssr_renders:renders,loads,
    wall_ms:performance.now()-started,cpu_microseconds:usage,
    process_memory_snapshot_bytes:process.memoryUsage(),process_peak_rss_kib:process.resourceUsage().maxRSS,
    source_sha256:Object.fromEntries(["components/M01ScientificCourse.tsx","components/M01CourseDiagram.tsx","components/M01CourseExercise.tsx","data/m01-scientific-course.ts"]
      .map(name=>[name,createHash("sha256").update(fs.readFileSync("src/"+name)).digest("hex")])),
    product_browser_qa:false,host_admission:false,field_eligibility:false}));
} finally {await server.close();}
"""
    result = subprocess.run([node, "--input-type=module", "-e", script], cwd=ROOT / "frontend",
                            capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert result.returncode == 0, result.stderr[-2000:]  # bounded local diagnostic, never a web error
    assert not result.stderr.strip(), result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def frontend_checks():
    return frontend_runtime_audit()


def measure_single_layer():
    """Fresh-process single-layer/height comparison, no extra catalogue/export."""
    started, cpu = time.perf_counter(), time.process_time()
    request, _ = control_request(case=0, noisy=True)
    request["config"].update(depths_m=[700.0], dampings=[100.0], heights_m=[300.0])
    original = digest(request)
    result = transform_survey(request)
    require(digest(request) == original and result["selection"]["status"] == "passed")
    return {"kind": "single_layer_single_height_authored_control", "request_sha256": original,
            "result_sha256": digest(result), "source_pins": PINS,
            "test_module_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "runtime": {"python": platform.python_version(), "engines": ENGINES},
            "wall_seconds": time.perf_counter() - started, "process_cpu_seconds": time.process_time() - cpu,
            "process_peak_working_set_bytes": peak_working_set_bytes(),
            "selection": result["selection"] | {"candidates": "retained in memory; not an extra teaching record"},
            "condition": result["condition"], "evaluation": result["evaluation"],
            "grid_nodes": len(result["grids"][0]["covered"]), "full_method_accepted": False}


def produce_course_records(output):
    """Frozen entry: actual case0/1/2 -> unchanged transform -> exporter."""
    output = owned_output(output)  # before control/kernel/plot allocation
    require(platform.python_implementation() == "CPython" and platform.python_version().startswith("3.12."))
    require({name: version(name) for name in ENGINES} == ENGINES)
    for name, pin in PINS.items():
        path = (ROOT / "data-pipeline" / name).resolve()
        require(sha256(path.read_bytes()).hexdigest() == pin)
        module = sys.modules.get(path.stem)
        if module is not None:
            require(Path(module.__file__).resolve() == path)
    output.mkdir(parents=True, exist_ok=False)
    catalogue, measurements = [], []
    started, cpu_started = time.perf_counter(), time.process_time()
    for case, scenario in enumerate(IDS):
        before, cpu_before = time.perf_counter(), time.process_time()
        request, truth = control_request(case=case, noisy=True)
        original = digest(request)
        result = transform_survey(request)
        require(digest(request) == original and result["selection"]["status"] == "passed")
        export_bundle(request, result, output / scenario)
        item = {
            "schema_version": "m01-course-record-1", "scenario_id": scenario,
            "label_kind": "synthetic_control_replay", "request_sha256": digest(request),
            "result_sha256": digest(result), "source_pins": dict(PINS),
            "runtime": {"python": platform.python_version(), "python_implementation": platform.python_implementation(),
                        "engines": dict(result["provenance"]["engines"])},
            "artifacts": [],
        }
        for role, name in ROLES.items():
            raw = (output / scenario / name).read_bytes()
            item["artifacts"].append({"role": role, "path": scenario + "/" + name,
                                      "bytes": len(raw), "sha256": sha256(raw).hexdigest()})
        validate_record(item, output, expected_result=result)
        # Independent source physics is evaluation only; never feeds the fit.
        oracle = hm.prism_gravity(truth["coordinates"], truth["prisms"], truth["densities"], field="g_z", parallel=False)
        difference = float(np.max(np.abs(oracle - truth["true_observed_mgal"])))
        require(difference < 1e-7)
        measurements.append({
            "scenario_id": scenario, "wall_seconds": time.perf_counter() - before,
            "process_cpu_seconds": time.process_time() - cpu_before,
            "process_peak_working_set_bytes": peak_working_set_bytes(),
            "bundle_bytes": sum(a["bytes"] for a in item["artifacts"]),
            "oracle_max_abs_mgal": difference, "evaluation": result["evaluation"],
            "selection": {k: result["selection"][k] for k in ("status", "depth_m", "damping", "height_m")},
            "split_sha256": result["split"]["sha256"], "condition": result["condition"],
            "grid_summaries": [{k: g[k] for k in ("height_m", "max_conditional_sigma_mgal",
                                                   "height_precision_passed", "adjacent_easting_difference_rms_mgal")}
                               | {"covered_count": sum(g["covered"]), "node_count": len(g["covered"])} for g in result["grids"]],
        })
        catalogue.append(item)
    write_new_json(output / "producer-measurements.json", {
        "producer_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "runtime": catalogue[0]["runtime"], "source_pins": PINS, "cases": measurements,
        "wall_seconds": time.perf_counter() - started, "process_cpu_seconds": time.process_time() - cpu_started,
        "process_peak_working_set_bytes": peak_working_set_bytes(),
        "limits": "Measured one process on this machine; no browser, device, field, host or full-method acceptance.",
    })
    write_new_json(output / INDEX.name, catalogue)  # completion marker last
    return catalogue


@pytest.fixture(scope="module")
def controls():
    return [control_request(case=i, noisy=True) for i in range(3)]


@pytest.fixture(scope="module")
def records():
    selected = os.environ.get("M01_COURSE_CANDIDATE_ROOT")
    base = Path(selected).resolve() if selected else WEB
    if selected:
        assert base.is_relative_to(OWNED_RUN_ROOT.resolve())
    index = base / INDEX.name if selected else INDEX
    assert index.is_file(), "Actual course records have not been produced/published."
    catalogue = read_request(index)
    assert type(catalogue) is list and len(catalogue) == 3
    return [(read_request(base / item["scenario_id"] / "request.json"),
             read_request(base / item["scenario_id"] / "result.json"),
             item) for item in catalogue]


def parent_from_control(request):
    parent = deepcopy(request["correction_result"]["dataset"])
    parent.update(state="observed_absolute", history=[])
    for row in parent["stations"]:
        row["value_mgal"] = row["original_value"]
    return parent


def adapter_request(parent, config):
    return {"schema_version": "gravity-station-adapter-request-1",
            "method": "gravity.station-corrections/v1", "dataset": parent,
            "config": config, "input_dataset_sha256": digest(parent),
            "submitted_config_sha256": digest(config)}


def somigliana(latitude):
    f, ge, gp = 1 / 298.257223563, 9.7803253359, 9.8321849378
    k, e2 = (1 - f) * gp / ge - 1, 2 * f - f**2
    s = np.sin(np.radians(latitude))**2
    return ge * (1 + k * s) / np.sqrt(1 - e2 * s) * 1e5


def test_scope_and_acceptance_boundaries(controls):
    for name, pin in PINS.items():
        assert sha256((ROOT / "data-pipeline" / name).read_bytes()).hexdigest() == pin
    for request, _ in controls:
        corrected = request["correction_result"]
        assert corrected["dataset"]["metadata"]["source_kind"] == "synthetic_control"
        assert corrected["processing"]["full_method_accepted"] is False
        assert corrected["qc"]["excluded_station_ids"] == []
    narrative = (COURSE / "README.md").read_text(encoding="utf-8")
    assert "field" in narrative and "M01" in narrative


def test_reference_height_formula_and_no_double_correction(controls):
    latitude = np.array([-90, -60, -45, 0, 45, 60, 90])
    np.testing.assert_allclose(normal_gravity(latitude, 0), somigliana(latitude),
                               rtol=0, atol=1e-5)
    assert float(normal_gravity(45, 1000)) == pytest.approx(980311.28969268, abs=1e-7)
    parent = parent_from_control(controls[0][0])
    row = parent["stations"][0]
    row.update(latitude_deg=45.0, receiver_height_m=1000.0,
               original_value=980311.28969268, value_mgal=980311.28969268)
    cfg = {"target": "gravity_disturbance", "uncertainty_model": "independent_first_order"}
    result = process_survey(parent, cfg)
    assert result["qc"]["derived_mgal"][0] == pytest.approx(0, abs=1e-7)
    assert result["dataset"]["history"][1]["additions_mgal"][0] == pytest.approx(308.48724505, abs=1e-7)
    with pytest.raises(GravityContractError, match="double correction"):
        process_survey(result["dataset"], cfg)


def test_datum_plate_and_supplied_terrain_contract(controls):
    parent = parent_from_control(controls[0][0])
    parent["metadata"].update(height_datum="orthometric", geoid_model="Authored constant N=30 m")
    for row in parent["stations"]:
        row.update(receiver_height_m=970.0, surface_height_m=870.0, geoid_m=30.0, geoid_sigma_m=0.0)
    cfg = {"target": "bouguer_disturbance", "uncertainty_model": "conservative_marginals",
           "density_kg_m3": 2670.0, "density_sigma_kg_m3": 0.0}
    result = process_survey(parent, cfg)
    assert result["qc"]["surface_ellipsoidal_m"] == [900.0] * 196
    assert result["dataset"]["history"][2]["additions_mgal"][0] == pytest.approx(-C * 2670 * 900, abs=1e-10)
    ids = [r["station_id"] for r in parent["stations"]]
    terrain = {"kind": "additive_residual_to_plate", "unit": "mGal",
               "height_reference": "WGS84_ellipsoid", "density_kg_m3": 2670.0,
               "source_sha256": digest({"authored": "signed residual"}), "method": "Authored T=B-A_topo, no DEM",
               "station_ids": ids, "additions_mgal": [-2.0] * 196, "sigma_mgal": [0.2] * 196}
    resumed = process_survey(result["dataset"], {**cfg, "target": "terrain_adjusted_disturbance", "terrain": terrain})
    np.testing.assert_allclose(resumed["qc"]["derived_mgal"], np.array(result["qc"]["derived_mgal"]) - 2, rtol=0, atol=1e-10)
    process_survey(parent, {**cfg, "terrain": None})  # null is valid for nonterrain
    for key, value in (("kind", "DEM_effect"), ("density_kg_m3", 2500),
                       ("height_reference", "unknown"), ("station_ids", ids[::-1])):
        with pytest.raises(GravityContractError):
            process_survey(parent, {**cfg, "target": "terrain_adjusted_disturbance", "terrain": {**terrain, key: value}})
    with pytest.raises(GravityContractError):
        process_survey(parent, {**cfg, "terrain": terrain})


def test_covariance_and_marginal_bound_definitions(controls):
    parent = parent_from_control(controls[0][0])
    parent["metadata"].update(height_datum="orthometric", geoid_model="Authored N, not a surveyed geoid")
    for row in parent["stations"]:
        row.update(latitude_deg=45.0, receiver_height_m=970.0, surface_height_m=870.0,
                   geoid_m=30.0, geoid_sigma_m=2.0, receiver_sigma_m=0.5, surface_sigma_m=0.7,
                   latitude_sigma_deg=0.0002)
    cfg = {"target": "bouguer_disturbance", "uncertainty_model": "independent_first_order",
           "density_kg_m3": 2670.0, "density_sigma_kg_m3": 20.0}
    result = process_survey(parent, cfg)
    components = result["processing"]["uncertainty_components_mgal"]
    gradient = -(3 * 980311.28969268 - 4 * 980345.55889093 + 980379.82987947) / (2 * (1000 / 9))
    assert components["geoid"][0] == pytest.approx((gradient - C * 2670) * 2, abs=1.2e-6)
    assert components["density"][0] == pytest.approx(C * 900 * 20, abs=1e-12)
    assert result["processing"]["uncertainty_mgal"][0] == pytest.approx(math.sqrt(sum(v[0]**2 for v in components.values())))
    bound = process_survey(parent, {**cfg, "uncertainty_model": "conservative_marginals"})
    assert bound["processing"]["uncertainty_mgal"][0] == pytest.approx(sum(v[0] for v in components.values()))
    # Rank-one shared density covariance: off-diagonal is not zero.
    u = C * np.array([900.0, 800.0]) * 20
    shared = np.outer(u, u)
    assert shared[0, 1] > 0 and np.linalg.eigvalsh(shared).min() > -1e-12
    del parent["stations"][0]["geoid_sigma_m"]
    with pytest.raises(GravityContractError):
        process_survey(parent, cfg)


def test_scalar_kernel_regularization_and_nonuniqueness(controls, records):
    for (request, truth), (_, result, _) in zip(controls, records, strict=True):
        coords = truth["coordinates"]
        independent = prism_integral(coords, truth["prisms"], truth["densities"], order=22)
        analytic = hm.prism_gravity(coords, truth["prisms"], truth["densities"], field="g_z", parallel=False)
        assert np.max(np.abs(independent - truth["true_observed_mgal"])) < 1e-7
        assert np.max(np.abs(independent - analytic)) < 1e-7
        points = tuple(np.asarray(p) for p in result["model"]["points_m"])
        j = hm.EquivalentSources(parallel=False).jacobian(tuple(c[:12] for c in coords), points)
        oracle = 1 / np.sqrt(sum((c[:12, None] - p[None, :])**2 for c, p in zip(coords, points, strict=True)))
        np.testing.assert_allclose(j, oracle, rtol=0, atol=1e-12)
        fits = [a for a in result["nonuniqueness"]["training_only_alternatives"]
                if a["status"] == "passed" and a["training_rmse_mgal"] < 0.02]
        assert len({a["depth_m"] for a in fits}) >= 2
        assert max(a["coefficient_l2_mgal_m"] for a in fits) > 2 * min(a["coefficient_l2_mgal_m"] for a in fits)
        assert "not density" in result["model"]["interpretation"]
    request, _ = controls[0]
    coords, values, sigma, covariance, active = admit(request)
    idx = active[:24]
    xyz = tuple(c[idx] for c in coords)
    engine, scale, transfer, _ = fit_layer(xyz, values[idx], sigma[idx], 360, 100, 1e10)
    j = engine.jacobian(xyz, engine.points_)
    direct = np.linalg.solve(j.T @ (j / sigma[idx, None]**2) + 100 * np.diag(scale**2), j.T / sigma[idx]**2)
    target = (xyz[0][:5], xyz[1][:5], np.full(5, 600.0))
    left = (engine.jacobian(target, engine.points_) / scale) @ transfer
    right = engine.jacobian(target, engine.points_) @ direct
    np.testing.assert_allclose(left, right, rtol=1e-7, atol=1e-9)
    cov = covariance[np.ix_(idx, idx)]
    np.testing.assert_allclose(left @ cov @ left.T, right @ cov @ right.T, rtol=1e-7, atol=1e-12)


def test_blocked_training_only_selection(controls, records):
    for _, result, _ in records:
        split = result["split"]
        blocks = dict(zip(split["active_indices"], split["block_ids_active"], strict=True))
        assert {blocks[i] for i in split["train_indices"]}.isdisjoint(blocks[i] for i in split["holdout_indices"])
        for candidate in result["selection"]["candidates"]:
            for fold in candidate["folds"]:
                assert set(fold["train_indices"]).isdisjoint(fold["validation_indices"])
                assert set(fold["train_indices"] + fold["validation_indices"]) <= set(split["train_indices"])
    request = deepcopy(controls[0][0])
    result = records[0][1]
    parent = parent_from_control(request)
    for i in result["split"]["holdout_indices"]:
        parent["stations"][i]["original_value"] += 7
        parent["stations"][i]["value_mgal"] = parent["stations"][i]["original_value"]
    request["correction_result"] = process_survey(parent, request["correction_result"]["processing"]["config"])
    changed = transform_survey(request)
    for key in ("selection", "model", "grids", "nonuniqueness"):
        assert changed[key] == result[key]
    assert changed["evaluation"]["holdout"]["rmse_mgal"] > 6


def test_continuation_support_height_and_residual_sign(controls, records):
    for (_, truth), (request, result, _) in zip(controls, records, strict=True):
        assert result["evaluation"]["holdout"]["covered_count"] >= 20
        assert result["evaluation"]["holdout"]["rmse_mgal"] < 0.1
        s = result["stations"]
        for i, covered in enumerate(s["prediction_covered"]):
            if covered:
                assert s["signed_predicted_minus_observed_mgal"][i] == pytest.approx(s["predicted_mgal"][i] - s["observed_mgal"][i], abs=1e-12)
            else:
                assert s["predicted_mgal"][i] is None
            if request["geometry"]["mask"][i]:
                assert result["split"]["partition"][i] == "masked" and not covered
        xx, yy = np.meshgrid(result["axes"]["easting_m"], result["axes"]["northing_m"])
        for i, grid in enumerate(result["grids"]):
            assert replay_grid(result, i) == pytest.approx(grid["predicted_mgal"], nan_ok=True)
            for keep, h, r, v, sd in zip(grid["covered"], grid["outside_hull"], grid["outside_radius"],
                                       grid["predicted_mgal"], grid["conditional_sigma_mgal"], strict=True):
                assert keep == (not h and not r)
                assert (v is not None and sd is not None) == keep
            idx = np.flatnonzero(grid["covered"])[::13]
            oracle = prism_integral((xx.ravel()[idx], yy.ravel()[idx], np.full(len(idx), grid["height_m"])),
                                    truth["prisms"], truth["densities"], order=22)
            assert np.sqrt(np.mean((np.array(grid["predicted_mgal"], dtype=float)[idx] - oracle)**2)) < 0.1
        assert result["uncertainty"]["kind"] == "conditional_linear_noise_propagation"
        assert result["selection"]["height_m"] == min(g["height_m"] for g in result["grids"] if g["height_precision_passed"])


def test_explanatory_controls_not_physical_jobs(frontend_checks):
    component = (ROOT / "frontend/src/components/M01CourseExercise.tsx").read_text(encoding="utf-8")
    data = (ROOT / "frontend/src/data/m01-scientific-course.ts").read_text(encoding="utf-8")
    assert all(e in data for e in ("E01", "E02", "E03", "E04"))
    assert "Apply" in component and "Reset" in component and "explanatory" in component.lower()
    assert "fetch(" not in component and "submitJob" not in component
    assert "calculateExplanation" in data
    assert frontend_checks["checks"] >= 30 and frontend_checks["negative_assertions"] >= 90
    assert frontend_checks["ssr_renders"] >= 150 and not frontend_checks["product_browser_qa"]


def test_recorded_scenario_identity_and_stale_negatives(records, controls, frontend_checks):
    selected = os.environ.get("M01_COURSE_CANDIDATE_ROOT")
    base = Path(selected).resolve() if selected else WEB
    catalogue = [item for _, _, item in records]
    for i, (request, result, item) in enumerate(records):
        validate_record(item, base)
        assert digest(request) == digest(controls[i][0])
        assert result == transform_survey(request)
    assert len({i["request_sha256"] for i in catalogue}) == 3
    assert len({i["result_sha256"] for i in catalogue}) == 3
    assert [load["scenario_id"] for load in frontend_checks["loads"]] == list(IDS)
    # Actual committed HEAD blobs, not Git's default normalized text dialect.
    if not selected:
        for item in catalogue:
            for entry in item["artifacts"]:
                blob = subprocess.run(["git", "show", "HEAD:data/derived/m01-scientific-course/" + entry["path"]],
                                      cwd=ROOT, capture_output=True, check=True).stdout
                assert blob == (base / entry["path"]).read_bytes()
                assert len(blob) == entry["bytes"] and sha256(blob).hexdigest() == entry["sha256"]
    original = catalogue[0]
    for key, value in (("scenario_id", "unknown"), ("source_pins", {**PINS, "gravity_processing.py": "0"*64}),
                       ("request_sha256", "0"*64), ("result_sha256", "0"*64),
                       ("extra", "forbidden")):
        bad = deepcopy(original)
        bad[key] = value
        with pytest.raises(ValueError):
            validate_record(bad, base)
    for key, value in (("bytes", original["artifacts"][0]["bytes"] + 1), ("sha256", "0"*64),
                       ("path", "../request.json"), ("role", "unknown")):
        bad = deepcopy(original)
        bad["artifacts"][0][key] = value
        with pytest.raises(ValueError):
            validate_record(bad, base)
    for count in (0, -1, True, 1.0):
        bad = deepcopy(original)
        bad["artifacts"][0]["bytes"] = count
        with pytest.raises(ValueError):
            validate_record(bad, base)


def test_user_file_workflow_and_parent_identity(controls, tmp_path):
    request = controls[0][0]
    parent = parent_from_control(request)
    config = {"target": "gravity_disturbance", "uncertainty_model": "independent_first_order"}
    selected = tmp_path / "user-selected-authored.json"
    selected.write_text(json.dumps({"dataset": parent, "config": config}), encoding="utf-8")
    loaded = read_request(selected)
    before = selected.read_bytes()
    result = run_station_corrections(adapter_request(loaded["dataset"], loaded["config"]))
    assert result["correction_result"] == process_survey(parent, config)
    assert result["receipt"]["acceptance"] == {"host_approved": False, "full_method_accepted": False, "field_source_verified": False}
    assert selected.read_bytes() == before
    absent = tmp_path / "absent.json"
    with pytest.raises(GravityContractError, match="regular file"):
        read_request(absent)
    assert not absent.exists()
    parent["stations"][0].update(original_value=980000.0, value_mgal=980000)
    native = run_station_corrections(adapter_request(parent, config))["correction_result"]
    assert native["processing"]["input_sha256"] == digest(parent)
    unreconstructable = {**request, "correction_result": native}
    with pytest.raises(GravityContractError, match="exact parent needed"):
        admit(unreconstructable)
    for chapter in COURSE.glob("*.md"):
        for block in chapter.read_text(encoding="utf-8").split("```python\n")[1:]:
            compile(block.split("```")[0], str(chapter), "exec")


def test_bilingual_questions_equations_and_physical_figures():
    for name in CHAPTERS:
        text = (COURSE / f"{name}.md").read_text(encoding="utf-8")
        assert "## English" in text and "## Español" in text
        assert "https://" in text and r"\[" in text
    assets = list((COURSE / "assets").glob("*.svg"))
    assert len(assets) == 6 and len({sha256(p.read_bytes()).hexdigest() for p in assets}) == 6
    for path in assets:
        svg = ET.parse(path).getroot()
        assert svg.get("viewBox") and svg.find("{http://www.w3.org/2000/svg}title") is not None
        assert "var(--" in path.read_text(encoding="utf-8")


def test_shared_shell_and_scoped_mount():
    for name in ("M01ScientificCourse", "M01CourseDiagram", "M01CourseExercise"):
        text = (ROOT / f"frontend/src/components/{name}.tsx").read_text(encoding="utf-8")
        assert "@fasl-work/caos-app-shell" in text
        assert ".css" not in text and "@font-face" not in text
    integration = (ROOT / "frontend/src/pages/Research.tsx").read_text(encoding="utf-8")
    assert 'import { M01ScientificCourse } from "../components/M01ScientificCourse";' in integration
    assert integration.count("content: <M01ScientificCourse />") == 2
    # Actual theory/implementation source mounts, not an initiative checklist.
    # This remains distinct from real rendered browser acceptance.


def test_negative_controls_and_field_gate(controls):
    request = controls[0][0]
    for section, key, value in (("geometry", "coordinate_unit", "km"), ("geometry", "data_unit", "microGal"),
                                ("geometry", "component", "g_z_upward"), ("config", "heights_m", [100.0])):
        bad = deepcopy(request)
        bad[section][key] = value
        with pytest.raises(GravityContractError):
            admit(bad)
    for key in ("easting_m", "northing_m", "upward_m"):
        bad = deepcopy(request)
        bad["geometry"][key][83] = None
        with pytest.raises(GravityContractError):
            admit(bad)
    for section, key in (("metadata", "height_datum"), ("stations", "gravity_sigma")):
        parent = parent_from_control(request)
        del (parent[section] if section == "metadata" else parent[section][0])[key]
        with pytest.raises(GravityContractError):
            process_survey(parent, request["correction_result"]["processing"]["config"])
    parent = parent_from_control(request)
    for row in parent["stations"]:
        row["gravity_sigma"] = 1.0
    noisy = deepcopy(request)
    noisy["correction_result"] = process_survey(parent, request["correction_result"]["processing"]["config"])
    with pytest.raises(GravityContractError, match="noise"):
        admit(noisy)
    stale = deepcopy(request)
    stale["correction_result"]["processing"]["input_sha256"] = "0"*64
    with pytest.raises(GravityContractError):
        admit(stale)
    assert request["correction_result"]["processing"]["full_method_accepted"] is False
    # No private field bytes or fabricated field SD/datum are consumed here.


def test_stage_authorization_and_nonclaims(tmp_path, monkeypatch):
    text = (FEATURE / "validation.md").read_text(encoding="utf-8")
    assert "--produce-course-records OUTPUT_ROOT" in text and "fresh absent output" in text
    assert "full_method_accepted=false" in text and "not rendered browser acceptance" in text
    monkeypatch.setitem(globals(), "OWNED_RUN_ROOT", tmp_path / "owned")
    for path in (tmp_path, tmp_path / "other", tmp_path / "owned"):
        with pytest.raises(ValueError):
            owned_output(path)
    fresh = tmp_path / "owned" / "fresh"
    assert owned_output(fresh) == fresh.resolve() and not fresh.exists()
    fresh.mkdir(parents=True)
    with pytest.raises(ValueError):
        produce_course_records(fresh)
    sized = tmp_path / "bytes.bin"
    sized.write_bytes(b"12345")
    for expected in (4, 6):
        with pytest.raises(ValueError):
            bound_bytes(sized, expected)
    assert bound_bytes(sized, 5) == b"12345"
    for raw in (b'{"x":NaN}', b'{"x":1e999}', b'{"x":1,"x":2}', b"\xff"):
        with pytest.raises(ValueError):
            strict_json(raw)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--produce-course-records":
        print("Usage: test_m01_scientific_course.py --produce-course-records OUTPUT_ROOT", file=sys.stderr)
        raise SystemExit(2)
    try:
        produce_course_records(sys.argv[2])
    except (ValueError, OSError, GravityContractError):
        print("Course production rejected; no verified complete record publication.", file=sys.stderr)
        raise SystemExit(2)
    print("Three authored-control bundles verified; no field, host or full-method acceptance.")
