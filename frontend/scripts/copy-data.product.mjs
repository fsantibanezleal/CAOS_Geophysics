import { createHash } from 'node:crypto';
import { cpSync, existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, isAbsolute, join, relative, resolve } from 'node:path';
import { gunzipSync, gzipSync } from 'node:zlib';

const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
const inside = (root, rel) => {
  if (typeof rel !== 'string' || rel === '' || isAbsolute(rel) || /^[a-z]:/i.test(rel)) return false;
  const resolved = resolve(root, rel);
  const from = relative(root, resolved);
  return from !== '' && from !== '..' && !from.startsWith(`..${process.platform === 'win32' ? '\\' : '/'}`) && !isAbsolute(from);
};

function pin(source, targetRoot, rel, bytes, digest, maxBytes) {
  if (!inside(targetRoot, rel) || !Number.isSafeInteger(bytes) || bytes < 1 || bytes > maxBytes || !/^[0-9a-f]{64}$/.test(digest)) {
    throw new Error(`invalid public artifact declaration: ${rel}`);
  }
  const stat = lstatSync(source);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size !== bytes || sha256(readFileSync(source)) !== digest) {
    throw new Error(`public artifact identity mismatch: ${source}`);
  }
  const target = join(targetRoot, rel);
  mkdirSync(dirname(target), { recursive: true });
  cpSync(source, target);
  return rel.replaceAll('\\', '/');
}

function productIndex(repo, rel) {
  const path = join(repo, rel);
  const stat = lstatSync(path);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 256 * 1024) throw new Error(`invalid product public index: ${rel}`);
  return JSON.parse(readFileSync(path, 'utf8'));
}

function recursiveFiles(root) {
  const out = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const path = join(root, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`symbolic link in reviewed public source: ${path}`);
    if (entry.isDirectory()) out.push(...recursiveFiles(path));
    else if (entry.isFile()) out.push(path);
    else throw new Error(`unsupported file entry in reviewed public source: ${path}`);
  }
  return out;
}

export default function copyProductData({ derived, out, repo }) {
  const copied = [];
  const problems = [];
  try {
    const catalog = JSON.parse(readFileSync(join(out, 'v2/catalog.json'), 'utf8'));
    if (catalog.schema !== 'inverse-earth.catalog/v2' || catalog.complete !== true || catalog.cases.length !== 20) {
      throw new Error('copied v2 catalog is not the reviewed complete 20-case release');
    }
    for (const c of catalog.cases) {
      if (!Array.isArray(c.variants) || c.variants.length !== 6) throw new Error(`${c.id}: expected six variants in copied catalog`);
      for (const v of c.variants) {
        const rel = `v2/${v.path}`;
        if (!inside(out, rel) || !Number.isSafeInteger(v.bytes) || !/^[0-9a-f]{64}$/.test(v.sha256)) throw new Error(`${c.id}: invalid catalog artifact binding`);
        const target = join(out, rel);
        if (!existsSync(target) || lstatSync(target).size !== v.bytes) throw new Error(`${c.id}: copied artifact size mismatch: ${rel}`);
      }
    }

    const phaseRoot = join(derived, 'phase/browser-assets/stead');
    const phase = JSON.parse(readFileSync(join(phaseRoot, 'manifest.json'), 'utf8'));
    const phaseNames = new Set([
      'manifest.json', 'ATTRIBUTION.md', phase.benchmark?.file,
      ...(Array.isArray(phase.records) ? phase.records.map((record) => record.waveform_file).filter(Boolean) : []),
    ]);
    const modelFile = phase.model?.file;
    const modelSourceFile = phase.model?.source_file ?? modelFile;
    if (modelSourceFile !== modelFile) phaseNames.add(modelSourceFile);
    if (phase.records?.length !== 24 || phase.selection?.qc_valid !== 23 || phase.selection?.qc_rejected !== 1 ||
        typeof modelFile !== 'string' || typeof modelSourceFile !== 'string' ||
        [...phaseNames].some((name) => typeof name !== 'string' || !/^[A-Za-z0-9_.-]+$/.test(name))) {
      throw new Error('STEAD browser asset manifest does not list the expected reviewed records');
    }
    for (const name of phaseNames) {
      const source = join(phaseRoot, name);
      const stat = lstatSync(source);
      if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 12 * 1024 * 1024) throw new Error(`invalid STEAD browser asset ${name}`);
      if (name === modelSourceFile && modelSourceFile !== modelFile) continue;
      const rel = `phase/stead/${name}`;
      mkdirSync(dirname(join(out, rel)), { recursive: true });
      cpSync(source, join(out, rel));
      copied.push(rel);
    }
    if (modelSourceFile !== modelFile) {
      const compressed = readFileSync(join(phaseRoot, modelSourceFile));
      if (compressed.byteLength !== phase.model.source_bytes || sha256(compressed) !== phase.model.source_sha256 ||
          compressed.byteLength > 5 * 1024 * 1024) {
        throw new Error('STEAD compressed ONNX source differs from its declared identity or size bound');
      }
      const modelBytes = gunzipSync(compressed);
      if (modelBytes.byteLength !== phase.model.bytes || sha256(modelBytes) !== phase.model.sha256) {
        throw new Error('STEAD decompressed ONNX bytes differ from the public model identity');
      }
      const target = join(out, 'phase/stead', modelFile);
      mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, modelBytes);
      copied.push(`phase/stead/${modelFile}`);
    }

    const modelRoot = join(repo, 'models/experimental/m12-physics-cuda-20261004');
    const modelReceipt = JSON.parse(readFileSync(join(modelRoot, 'm12-physics-browser-receipt.json'), 'utf8'));
    const trainingReceipt = JSON.parse(readFileSync(join(modelRoot, 'receipt.json'), 'utf8'));
    const modelBytes = readFileSync(join(modelRoot, 'm12-physics.onnx'));
    const modelSha = '92e5a3cc5bc70d81c122a1d64c2b4bd722eed47cfa55e2f2473f755cf499f261';
    const checkpointSha = '23d51c42b079f37c85fe77796556962e9b7f4f2fe179650a329641a6faa9ded1';
    if (modelReceipt.schema !== 'geophysics.m12-browser-model/v1' || modelReceipt.status !== 'parity-verified' ||
        modelReceipt.model?.sha256 !== modelSha || sha256(modelBytes) !== modelSha ||
        modelReceipt.checkpoint?.sha256 !== checkpointSha || trainingReceipt.schema !== 'geophysics.m12-physics/v2' ||
        trainingReceipt.checkpoint_sha256 !== checkpointSha || modelReceipt.training?.scientific_verdict !== 'failed-held-out-comparator' ||
        modelReceipt.parity?.passed !== true || modelReceipt.parity?.records !== 640 || modelReceipt.parity?.max_absolute_error_m_s > 0.002) {
      throw new Error('M12 model, checkpoint, negative scientific verdict or browser parity receipt changed');
    }
    const receiptBytes = readFileSync(join(modelRoot, 'm12-physics-browser-receipt.json'));
    if (modelReceipt.model.bytes !== modelBytes.byteLength || modelReceipt.training?.receipt_sha256 !== sha256(readFileSync(join(modelRoot, 'receipt.json')))) {
      throw new Error('M12 browser receipt does not bind the exact model and training receipt bytes');
    }
    copied.push(pin(join(modelRoot, 'm12-physics.onnx'), out, 'models/m12-physics-v2/m12-physics.onnx', modelBytes.byteLength, modelSha, 16 * 1024 * 1024));
    copied.push(pin(join(modelRoot, 'm12-physics-browser-receipt.json'), out, 'models/m12-physics-v2/m12-physics-browser-receipt.json', receiptBytes.byteLength, sha256(receiptBytes), 64 * 1024));

    const courseIndex = productIndex(repo, 'frontend/src/data/m01-course-record-index.json');
    if (!Array.isArray(courseIndex) || courseIndex.length !== 3) throw new Error('M01 course index must declare three reviewed synthetic cases');
    const courseSource = join(derived, 'm01-scientific-course');
    const courseFiles = courseIndex.flatMap((record, i) => {
      if (record.scenario_id !== `prism-case-${i}` || record.label_kind !== 'synthetic_control_replay' || record.artifacts?.length !== 11) {
        throw new Error(`M01 course case ${i} has invalid scope or artifact count`);
      }
      return record.artifacts.map((artifact) => {
        if (!/^prism-case-[012]\/[a-z-]+\.(json|svg|png)$/.test(artifact.path)) throw new Error(`unsafe M01 course path ${artifact.path}`);
        return pin(join(courseSource, artifact.path), out, `m01-scientific-course/${artifact.path}`, artifact.bytes, artifact.sha256, 32 * 1024 * 1024);
      });
    });
    if (new Set(courseFiles).size !== 33) throw new Error('M01 course artifact paths are not unique');
    copied.push(...courseFiles);

    const fieldIndex = productIndex(repo, 'frontend/src/data/field-study-index.json');
    if (fieldIndex.schema !== 'geophysics.field-study-index/v1' || fieldIndex.artifacts?.length !== 2) throw new Error('field study index must declare the two reviewed public records');
    const fieldPaths = new Set(['long-valley/1982-06_to_1999-07.json', 'amargosa/amargosa-m03-20261111.json']);
    if (new Set(fieldIndex.artifacts.map((field) => field.path)).size !== fieldPaths.size ||
        fieldIndex.artifacts.some((field) => !fieldPaths.has(field.path))) throw new Error('field-study index paths differ from the reviewed public records');
    copied.push(...fieldIndex.artifacts.map((field) => pin(join(derived, 'field', field.path), out,
      `field/${field.path}`, field.bytes, field.sha256, 2 * 1024 * 1024)));

    const ediRoot = join(derived, 'v2', 'edi');
    const ediManifestPath = join(ediRoot, 'manifest.json');
    const ediManifestBytes = readFileSync(ediManifestPath);
    const edi = JSON.parse(ediManifestBytes.toString('utf8'));
    if (edi.schema !== 'inverse-earth/edi-bundle/v1' || edi.fixtures?.length !== 3 ||
        edi.field_screens?.length !== 1 || edi.calibration?.length !== 2) {
      throw new Error('EDI bundle manifest differs from the reviewed fixture, field-screen, and calibration inventory');
    }
    const ediFiles = [{ path: 'manifest.json', bytes: ediManifestBytes.byteLength, sha256: sha256(ediManifestBytes) }];
    for (const fixture of edi.fixtures) {
      for (const [path, digest] of [[fixture.source, fixture.source_sha256], [fixture.artifact, fixture.artifact_sha256]]) {
        ediFiles.push({ path, bytes: lstatSync(join(ediRoot, path)).size, sha256: digest });
      }
    }
    for (const field of edi.field_screens) {
      ediFiles.push({ path: field.artifact, bytes: field.artifact_bytes, sha256: field.artifact_sha256 });
    }
    for (const calibration of edi.calibration) {
      const source = join(ediRoot, calibration.artifact);
      const size = calibration.artifact_bytes ?? lstatSync(source).size;
      ediFiles.push({ path: calibration.artifact, bytes: size, sha256: calibration.artifact_sha256 });
    }
    if (new Set(ediFiles.map((file) => file.path)).size !== ediFiles.length ||
        ediFiles.some((file) => typeof file.path !== 'string' || !/^[a-z0-9][a-z0-9.-]*$/i.test(file.path))) {
      throw new Error('EDI bundle manifest contains duplicate or unsafe artifact names');
    }
    copied.push(...ediFiles.map((file) => pin(
      join(ediRoot, file.path), out, `v2/edi/${file.path}`,
      file.bytes, file.sha256, 16 * 1024 * 1024,
    )));

    const fwiRoot = join(out, 'v2');
    for (const path of recursiveFiles(fwiRoot).filter((p) => /[\\/]FWI_[A-Z0-9_]+[\\/].+\.json$/.test(p))) {
      const rel = relative(out, path).replaceAll('\\', '/');
      writeFileSync(`${path}.gz`, gzipSync(readFileSync(path), { level: 9, mtime: 0 }));
      copied.push(`${rel}.gz`);
    }
  } catch (error) {
    problems.push(error instanceof Error ? error.message : String(error));
  }
  return { copied, absent: [], problems };
}
