import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '::1', '[::1]'])

function parseBoolean(value, fallback = false) {
  if (value === undefined || value === null || value === '') return fallback
  const normalized = String(value).trim().toLowerCase()
  if (['1', 'true', 'yes', 'on'].includes(normalized)) return true
  if (['0', 'false', 'no', 'off'].includes(normalized)) return false
  return fallback
}

function resolveLocalMode(mode, env) {
  const explicit = String(env.VITE_LOCAL_MODE || '').trim().toLowerCase()
  if (explicit === 'backend') return 'backend'
  if (explicit === 'mock') return 'mock'
  if (mode === 'backend') return 'backend'
  return 'mock'
}

function isLoopbackOrigin(target) {
  try {
    const url = new URL(target)
    return LOOPBACK_HOSTS.has(url.hostname.toLowerCase())
  } catch {
    return false
  }
}

function buildApiProxy(target) {
  return {
    '/api': {
      target,
      changeOrigin: true,
    },
    '/docs': {
      target,
      changeOrigin: true,
    },
    '/openapi.json': {
      target,
      changeOrigin: true,
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const localMode = resolveLocalMode(mode, env)
  const backendOrigin = String(env.VITE_LOCAL_BACKEND_ORIGIN || 'http://localhost:8000').trim()
  const allowRemoteApi = parseBoolean(env.VITE_ALLOW_REMOTE_API, false)

  if (localMode === 'backend' && !allowRemoteApi && !isLoopbackOrigin(backendOrigin)) {
    throw new Error(
      `[local-mode] Refusing backend proxy target '${backendOrigin}'. Use localhost/127.0.0.1/::1 or set VITE_ALLOW_REMOTE_API=true.`
    )
  }

  return {
    plugins: [
      vue(),
      mode !== 'production' && vueDevTools(),
    ].filter(Boolean),
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: env.VITE_DEV_HOST || '127.0.0.1',
      port: Number(env.VITE_DEV_PORT || 5173),
      strictPort: false,
      proxy: localMode === 'backend' ? buildApiProxy(backendOrigin) : undefined,
    },
  }
})
