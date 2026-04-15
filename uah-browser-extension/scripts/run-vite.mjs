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

const cwd = fileURLToPath(new URL('../', import.meta.url))
const args = process.argv.slice(2)

function runVite(viteArgs) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [viteBin, ...viteArgs], {
      stdio: 'inherit',
      cwd,
      env: process.env,
    })

    child.on('error', reject)
    child.on('exit', (code) => {
      if ((code ?? 0) === 0) {
        resolve()
        return
      }
      reject(new Error(`Vite exited with code ${code ?? 1}`))
    })
  })
}

async function main() {
  if (args[0] === 'build') {
    const buildArgs = args.slice(1)
    await runVite(['build', ...buildArgs])
    await runVite(['build', '--config', 'vite.autofill.config.mjs', ...buildArgs])
    await runVite(['build', '--config', 'vite.pinned.config.mjs', ...buildArgs])
    return
  }

  await runVite(args)
}

main().catch((error) => {
  console.error(error?.message || error)
  process.exit(1)
})
