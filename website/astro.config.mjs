import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

// CF_PAGES_URL is provided automatically by Cloudflare Pages at build time.
export default defineConfig({
  site: process.env.SITE_URL || process.env.CF_PAGES_URL || undefined,
  output: 'static',
  devToolbar: { enabled: false },
  vite: { plugins: [tailwindcss()], build: { assetsInlineLimit: 0 } },
  server: { host: '0.0.0.0', port: 4173, allowedHosts: ['terminal.local'] },
});
