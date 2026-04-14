import { existsSync, readFileSync } from 'node:fs'
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
  if (mode === 'backend') return 'backend'
  if (mode === 'mock') return 'mock'

  const explicit = String(env.VITE_LOCAL_MODE || '').trim().toLowerCase()
  if (explicit === 'backend') return 'backend'
  if (explicit === 'mock') return 'mock'
  return 'backend'
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

function resolveHttpsConfig(env) {
  const httpsEnabled = parseBoolean(env.VITE_DEV_HTTPS, false)
  if (!httpsEnabled) return false

  const certFile = String(env.VITE_DEV_HTTPS_CERT_FILE || '').trim()
  const keyFile = String(env.VITE_DEV_HTTPS_KEY_FILE || '').trim()

  if (!certFile || !keyFile) {
    throw new Error(
      '[local-https] Set both VITE_DEV_HTTPS_CERT_FILE and VITE_DEV_HTTPS_KEY_FILE when VITE_DEV_HTTPS=true.'
    )
  }
  if (!existsSync(certFile)) {
    throw new Error(`[local-https] HTTPS cert file was not found: ${certFile}`)
  }
  if (!existsSync(keyFile)) {
    throw new Error(`[local-https] HTTPS key file was not found: ${keyFile}`)
  }

  return {
    cert: readFileSync(certFile),
    key: readFileSync(keyFile),
  }
}

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isServe = command === 'serve'
  const localMode = resolveLocalMode(mode, env)
  const backendOrigin = String(env.VITE_LOCAL_BACKEND_ORIGIN || 'http://localhost:8000').trim()
  const allowRemoteApi = parseBoolean(env.VITE_ALLOW_REMOTE_API, false)
  const https = isServe ? resolveHttpsConfig(env) : false

  if (isServe && localMode === 'backend' && !allowRemoteApi && !isLoopbackOrigin(backendOrigin)) {
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
      host: env.VITE_DEV_HOST || 'localhost',
      port: Number(env.VITE_DEV_PORT || 5173),
      strictPort: false,
      https,
      proxy: localMode === 'backend' ? buildApiProxy(backendOrigin) : undefined,
    },
  }
})
