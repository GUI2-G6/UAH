import { existsSync } from 'node:fs'
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

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  resolveExtensionBuildConfig(env)

  return {
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
