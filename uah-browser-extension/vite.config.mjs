import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { buildManifest, resolveExtensionBuildConfig } from './manifest.config.mjs'

function resolveToolModule(relativePath) {
  const candidates = [
    new URL(`./node_modules/${relativePath}`, import.meta.url),
    new URL(`../frontend/node_modules/${relativePath}`, import.meta.url),
  ]

  for (const candidate of candidates) {
    if (existsSync(fileURLToPath(candidate))) {
      return candidate
    }
  }

  throw new Error(`Unable to resolve tool module '${relativePath}'. Install extension deps or ensure frontend/node_modules exists.`)
}

const { defineConfig, loadEnv } = await import(resolveToolModule('vite/dist/node/index.js').href)
const { default: vue } = await import(resolveToolModule('@vitejs/plugin-vue/dist/index.mjs').href)

function parseExplicitEnvFile(envFilePath) {
  const parsed = {}
  const lines = readFileSync(envFilePath, 'utf8').split(/\r?\n/)

  for (const rawLine of lines) {
    const trimmed = rawLine.trim()
    if (!trimmed || trimmed.startsWith('#')) {
      continue
    }

    const separatorIndex = trimmed.indexOf('=')
    if (separatorIndex <= 0) {
      continue
    }

    const key = trimmed.slice(0, separatorIndex).trim()
    if (!key) {
      continue
    }

    let value = trimmed.slice(separatorIndex + 1).trim()
    if (
      (value.startsWith('"') && value.endsWith('"'))
      || (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1)
    }

    parsed[key] = value
  }

  return parsed
}

function loadExtensionEnv(mode) {
  const env = loadEnv(mode, process.cwd(), '')
  const explicitEnvFile = String(process.env.UAH_EXTENSION_ENV_FILE || '').trim()
  if (!explicitEnvFile) {
    return env
  }

  const resolvedEnvFile = path.isAbsolute(explicitEnvFile)
    ? explicitEnvFile
    : path.resolve(process.cwd(), explicitEnvFile)

  if (!existsSync(resolvedEnvFile)) {
    throw new Error(`Configured UAH_EXTENSION_ENV_FILE was not found: ${resolvedEnvFile}`)
  }

  return {
    ...env,
    ...parseExplicitEnvFile(resolvedEnvFile),
  }
}

export default defineConfig(({ mode }) => {
  const env = loadExtensionEnv(mode)
  resolveExtensionBuildConfig(env)

  return {
    define: {
      'import.meta.env.VITE_EXTENSION_APP_ORIGIN': JSON.stringify(env.VITE_EXTENSION_APP_ORIGIN || ''),
      'import.meta.env.VITE_EXTENSION_API_ORIGIN': JSON.stringify(env.VITE_EXTENSION_API_ORIGIN || ''),
      'import.meta.env.VITE_EXTENSION_AUTH_NAMESPACE': JSON.stringify(env.VITE_EXTENSION_AUTH_NAMESPACE || ''),
      'import.meta.env.VITE_EXTENSION_AUTH_COOKIE_NAME': JSON.stringify(env.VITE_EXTENSION_AUTH_COOKIE_NAME || ''),
    },
    plugins: [
      vue(),
      {
        name: 'uah-extension-manifest',
        generateBundle() {
          this.emitFile({
            type: 'asset',
            fileName: 'manifest.json',
            source: JSON.stringify(buildManifest(env), null, 2),
          })
        },
      },
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        vue: fileURLToPath(resolveToolModule('vue/dist/vue.esm-bundler.js')),
      },
    },
    build: {
      outDir: 'dist',
      emptyOutDir: true,
      rollupOptions: {
        input: {
          popup: fileURLToPath(new URL('./popup.html', import.meta.url)),
          background: fileURLToPath(new URL('./src/background/index.js', import.meta.url)),
        },
        output: {
          entryFileNames: (chunk) => (chunk.name === 'background' ? 'background.js' : 'assets/[name].js'),
          chunkFileNames: 'assets/[name]-[hash].js',
          assetFileNames: 'assets/[name]-[hash][extname]',
        },
      },
    },
  }
})
