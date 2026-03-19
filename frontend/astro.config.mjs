// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  output: 'static',
  vite: {
    plugins: [tailwindcss()],
  },
  server: {
    // Bind on all interfaces so the dev server is reachable inside Docker
    host: true,
  },
});
