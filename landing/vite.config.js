import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendOrigin = String(process.env.VITE_LOCAL_BACKEND_ORIGIN || 'http://localhost:8000').trim()

export default defineConfig({
  plugins: [vue()],
  base: '/',
  server: {
    proxy: {
      '/api': {
        target: backendOrigin,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
