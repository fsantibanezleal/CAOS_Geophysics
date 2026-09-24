import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  base: './', // relative base -> works on a GitHub Pages project site
  publicDir: 'public-release', // only allowlisted assets, never stale v1 build overlays
  build:{rollupOptions:{output:{manualChunks:{three:['three'],shell:['@fasl-work/caos-app-shell'],react:['react','react-dom','react-router']}}}},
  plugins: [react()],
  test: { environment: 'node', globals: true },
});
