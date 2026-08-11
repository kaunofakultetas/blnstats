// -----------------------------------------------------------
//  [*] Vite configuration
//
//  Plugins:
//    - react       — JSX + fast refresh
//    - tailwindcss — Tailwind v4 (no tailwind.config file; the
//                    theme tokens live in src/globals.css)
//
//  Also sets up:
//    - '@' → src alias (matches imports like '@/components/...')
//    - dev server on 0.0.0.0:80 so the Docker dev container
//      (blnstats-vite, Dockerfile.dev) is reachable through
//      the Caddy endpoint
// -----------------------------------------------------------

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 80,
    allowedHosts: true,
  },
});
