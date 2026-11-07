import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  base: '/',
  publicDir: 'public-release', // only allowlisted assets, never stale v1 build overlays
  worker: { format: 'es' }, // M12 lazily loads ONNX Runtime WASM inside its calculation worker.
  resolve: { dedupe: ['react', 'react-dom', 'react-router'] },
  build:{rollupOptions:{output:{manualChunks:{three:['three'],shell:['@fasl-work/caos-app-shell'],react:['react','react-dom','react-router']}}}},
  plugins: [react()],
  test: { environment: 'node', globals: true, exclude: ['e2e/**', 'node_modules/**'] },
});
