import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  base: '/',
  publicDir: 'public', // the template rebuilds public/data from its declared-file index before each build
  worker: { format: 'es' }, // M12 lazily loads ONNX Runtime WASM inside its calculation worker.
  resolve: { dedupe: ['react', 'react-dom', 'react-router'] },
  build:{rollupOptions:{output:{manualChunks:{three:['three'],shell:['@fasl-work/caos-app-shell'],react:['react','react-dom','react-router']}}}},
  plugins: [react()],
  // M03's browser-side Pyodide setup times out when Vitest overlaps it with solver-heavy files.
  test: { environment: 'node', globals: true, maxWorkers: 1, exclude: ['e2e/**', 'node_modules/**'] },
});
