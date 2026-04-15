import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

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

const { defineConfig } = await import(resolveToolModule('vite/dist/node/index.js').href)

export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    cssCodeSplit: false,
    lib: {
      entry: path.resolve(fileURLToPath(new URL('./src/autofill/contentRuntime.entry.js', import.meta.url))),
      name: 'UAHAutofillContent',
      formats: ['iife'],
      fileName: () => 'autofill-content.js',
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
})
