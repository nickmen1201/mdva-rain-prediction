import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      // MapLibre GL pesa ~800 kB: en su propio chunk, cacheable entre versiones de la app
      output: { manualChunks: { maplibre: ['maplibre-gl'] } },
    },
    chunkSizeWarningLimit: 1100,
  },
  test: { environment: 'node' },
})
