import { spawn } from 'node:child_process'
import process from 'node:process'

const dockerCommand = process.platform === 'win32' ? 'docker.exe' : 'docker'
const windowsCommandShell = process.env.ComSpec || 'C:\\Windows\\System32\\cmd.exe'

const runningChildren = []
let shuttingDown = false

function buildCommand(command, args) {
    if (process.platform !== 'win32') {
        return {
            command,
            args,
        }
    }

    return {
        command: windowsCommandShell,
        args: ['/d', '/s', '/c', command, ...args],
    }
}

function runOnce(command, args, label) {
    return new Promise((resolve, reject) => {
        const invocation = buildCommand(command, args)
        const child = spawn(invocation.command, invocation.args, {
            stdio: 'inherit',
            shell: false,
            windowsHide: false,
        })

        child.on('error', (error) => {
            reject(new Error(`[local-dev] Failed to start ${label}: ${error.message}`))
        })

        child.on('exit', (code, signal) => {
            if (signal) {
                reject(new Error(`[local-dev] ${label} stopped by signal ${signal}`))
                return
            }
            if (code !== 0) {
                reject(new Error(`[local-dev] ${label} exited with code ${code}`))
                return
            }
            resolve()
        })
    })
}

function stopChildren(exitCode = 0) {
    if (shuttingDown) return
    shuttingDown = true

    for (const child of runningChildren) {
        if (!child.killed) {
            child.kill('SIGINT')
        }
    }

    setTimeout(() => {
        for (const child of runningChildren) {
            if (!child.killed) {
                child.kill('SIGTERM')
            }
        }
    }, 1500)

    setTimeout(() => {
        process.exit(exitCode)
    }, 2500)
}

function startLongRunning(command, args, label) {
    const invocation = buildCommand(command, args)
    const child = spawn(invocation.command, invocation.args, {
        stdio: 'inherit',
        shell: false,
        windowsHide: false,
    })

    runningChildren.push(child)

    child.on('error', (error) => {
        console.error(`[local-dev] Failed to start ${label}: ${error.message}`)
        stopChildren(1)
    })

    child.on('exit', (code, signal) => {
        if (shuttingDown) return

        if (signal === 'SIGINT' || signal === 'SIGTERM') {
            stopChildren(0)
            return
        }

        if (code && code !== 0) {
            console.error(`[local-dev] ${label} exited with code ${code}`)
            stopChildren(code)
            return
        }

        console.log(`[local-dev] ${label} exited.`)
        stopChildren(0)
    })
}

async function main() {
    console.log('[local-dev] Starting local backend profile (db-local + backend-local)...')
    await runOnce(
        dockerCommand,
        ['compose', '-f', 'docker-compose.local.yml', '--profile', 'backend', 'up', '-d', 'db-local', 'backend-local'],
        'docker compose backend profile'
    )

    console.log('[local-dev] Backend profile started.')
    console.log('[local-dev] Starting frontend mock server on http://localhost:5173 ...')
    startLongRunning('npm', ['--prefix', 'frontend', 'run', 'dev'], 'frontend dev server')

    console.log('[local-dev] Starting landing server on http://localhost:5174 ...')
    startLongRunning('npm', ['--prefix', 'landing', 'run', 'dev', '--', '--port', '5174'], 'landing dev server')

    console.log('[local-dev] Press Ctrl+C to stop the dev servers.')
    console.log('[local-dev] Backend containers remain running; use "npm run dev:local:down" to stop them.')

    await new Promise(() => { })
}

process.on('SIGINT', () => stopChildren(0))
process.on('SIGTERM', () => stopChildren(0))

main().catch((error) => {
    console.error(error.message)
    process.exit(1)
})
