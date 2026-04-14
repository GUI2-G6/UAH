import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const localVite = fileURLToPath(new URL('../node_modules/vite/bin/vite.js', import.meta.url))
const frontendVite = fileURLToPath(new URL('../../frontend/node_modules/vite/bin/vite.js', import.meta.url))

const viteBin = existsSync(localVite) ? localVite : frontendVite

if (!existsSync(viteBin)) {
  console.error(
    'Unable to locate Vite. Run `npm install` inside `uah-browser-extension/` or ensure `frontend/node_modules` exists.'
  )
  process.exit(1)
}

const child = spawn(process.execPath, [viteBin, ...process.argv.slice(2)], {
  stdio: 'inherit',
  cwd: fileURLToPath(new URL('../', import.meta.url)),
  env: process.env,
})

child.on('exit', (code) => {
  process.exit(code ?? 0)
})
