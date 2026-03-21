import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'prompt',
      strategies: 'injectManifest',
      srcDir: 'src',
      filename: 'sw.ts',
      includeAssets: ['icon-192.svg', 'icon-512.svg', 'icon-maskable-512.svg', 'offline.html'],
      manifest: {
        id: '/',
        name: 'Atum — Media Center',
        short_name: 'Atum',
        description: 'Busca, download e reprodução de mídia com player hi-fi',
        theme_color: '#0a0a0a',
        background_color: '#0a0a0a',
        display: 'standalone',
        orientation: 'any',
        categories: ['entertainment', 'music'],
        lang: 'pt-BR',
        start_url: '/',
        scope: '/',
        icons: [
          {
            src: '/icon-192.svg',
            sizes: '192x192',
            type: 'image/svg+xml',
            purpose: 'any',
          },
          {
            src: '/icon-512.svg',
            sizes: '512x512',
            type: 'image/svg+xml',
            purpose: 'any',
          },
          {
            src: '/icon-maskable-512.svg',
            sizes: '512x512',
            type: 'image/svg+xml',
            purpose: 'maskable',
          },
        ],
        shortcuts: [
          {
            name: 'Buscar',
            short_name: 'Busca',
            url: '/search',
            icons: [{ src: '/icon-192.svg', sizes: '192x192' }],
          },
          {
            name: 'Biblioteca',
            short_name: 'Biblioteca',
            url: '/library',
            icons: [{ src: '/icon-192.svg', sizes: '192x192' }],
          },
          {
            name: 'Downloads',
            short_name: 'Downloads',
            url: '/downloads',
            icons: [{ src: '/icon-192.svg', sizes: '192x192' }],
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,woff2}'],
        offlineGoogleAnalytics: false,
      },
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('react-dom') || id.includes('/react/') || id.includes('/scheduler/')) return 'react';
            if (id.includes('wavesurfer')) return 'wavesurfer';
            if (id.includes('react-router')) return 'router';
            if (id.includes('three') || id.includes('@react-three')) return 'three';
            if (id.includes('shaka-player')) return 'shaka';
            return 'vendor';
          }
        },
      },
    },
    chunkSizeWarningLimit: 950,
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
