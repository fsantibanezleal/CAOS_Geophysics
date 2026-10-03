import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig(({ mode }) => ({
  base: mode === 'single-origin' ? '/' : './',
  publicDir: 'public-release', // only allowlisted assets, never stale v1 build overlays
  build:{rollupOptions:{output:{manualChunks:{three:['three'],shell:['@fasl-work/caos-app-shell'],react:['react','react-dom','react-router']}}}},
  plugins: [react()],
  test: { environment: 'node', globals: true, exclude: ['e2e/**', 'node_modules/**'] },
}));
