import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, fs: { allow: ['../..'] } },
  build: { target: 'es2022', sourcemap: 'hidden' },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
