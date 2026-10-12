import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Ustaad',
        short_name: 'Ustaad',
        start_url: '/w',
        display: 'standalone',
        // manifest values can't read CSS variables: Graphite and Housing White from tokens.css
        theme_color: '#1d2327',
        background_color: '#eef1ef',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
        // docs/SPEC.md §8
        share_target: {
          action: '/d/import',
          method: 'POST',
          enctype: 'multipart/form-data',
          params: {
            files: [
              {
                name: 'files',
                accept: ['.zip', 'application/zip', '.opus', 'audio/ogg', 'audio/opus', 'text/plain', 'image/*'],
              },
            ],
          },
        },
      },
    }),
  ],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
})
