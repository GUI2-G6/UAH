import fs from "node:fs"
import path from "node:path"

const frontendRoot = path.resolve(process.cwd())
const srcRoot = path.join(frontendRoot, "src")

const allowedCssFiles = new Set([
  path.join("src", "components", "css", "Card.css"),
])

const bareCardSelectorPattern = /(^|[^\w-])\.(?:card|big-card)(?![-\w])/m
const cardTagWithClassPattern = /<Card\b[^>]*\bclass\s*=\s*["']([^"']*)["']/gi

function stripVueComments(input) {
  return input
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/\/\*[\s\S]*?\*\//g, "")
}

function stripCssComments(input) {
  return input.replace(/\/\*[\s\S]*?\*\//g, "")
}

function collectFiles(rootDir) {
  const entries = fs.readdirSync(rootDir, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    const fullPath = path.join(rootDir, entry.name)
    if (entry.isDirectory()) {
      files.push(...collectFiles(fullPath))
      continue
    }
    files.push(fullPath)
  }

  return files
}

const allFiles = collectFiles(srcRoot)
const violations = []

for (const fullPath of allFiles) {
  const relPath = path.relative(frontendRoot, fullPath)
  const source = fs.readFileSync(fullPath, "utf8")

  if (fullPath.endsWith(".vue")) {
    const cleaned = stripVueComments(source)
    for (const match of cleaned.matchAll(cardTagWithClassPattern)) {
      const classTokens = match[1].split(/\s+/).filter(Boolean)
      if (classTokens.includes("card") || classTokens.includes("big-card")) {
        violations.push(`${relPath}: avoid class="card" or class="big-card" on <Card>; use page-owned classes instead.`)
        break
      }
    }
  }

  if (fullPath.endsWith(".css") && !allowedCssFiles.has(relPath)) {
    const cleaned = stripCssComments(source)
    if (bareCardSelectorPattern.test(cleaned)) {
      violations.push(`${relPath}: bare .card/.big-card selector detected; target page-owned classes or the namespaced ui-card contract instead.`)
    }
  }
}

if (violations.length) {
  console.error("Shared card contract violations found:\n")
  for (const violation of violations) {
    console.error(`- ${violation}`)
  }
  process.exit(1)
}

console.log("Shared card contract check passed.")
