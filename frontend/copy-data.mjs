import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontend = dirname(fileURLToPath(import.meta.url));
const run = spawnSync(process.execPath, [join(frontend, 'scripts', 'prepare-data.mjs')], { stdio: 'inherit' });
process.exit(run.status ?? 1);
