import { existsSync } from 'node:fs';
import { isAbsolute, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const frontend = resolve(fileURLToPath(new URL('..', import.meta.url)));
const repo = resolve(frontend, '..');
const generated = spawnSync('python', [join(repo, 'scripts', 'build_frontend_data_contract.py')], { cwd: repo, encoding: 'utf8' });
if (generated.stdout) process.stdout.write(generated.stdout);
if (generated.stderr) process.stderr.write(generated.stderr);
if (generated.status !== 0) process.exit(generated.status ?? 1);

const env = { ...process.env };
const configured = env.GEOPHYSICS_LOCAL_DATA_ROOT?.trim();
if (configured && !isAbsolute(configured)) throw new Error('GEOPHYSICS_LOCAL_DATA_ROOT must be an absolute data root.');
const repositoryDerived = join(repo, 'data', 'derived');
const externalDerived = configured ? join(resolve(configured), 'data', 'derived') : null;
const selected = externalDerived && existsSync(join(externalDerived, 'manifests', 'index.json'))
  ? externalDerived
  : repositoryDerived;
env.CAOS_DATA_ROOT = selected;

const args = process.argv.slice(2);
if (args.length) throw new Error('Candidate overlays must be prepared through the validated data pipeline, not ad hoc build arguments.');
const copied = spawnSync(process.execPath, [join(frontend, 'scripts', 'copy-data.mjs')], { cwd: repo, env, stdio: 'inherit' });
process.exit(copied.status ?? 1);
