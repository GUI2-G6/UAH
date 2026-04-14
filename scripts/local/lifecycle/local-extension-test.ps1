[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$SkipFrontend,
    [switch]$BackendOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Fail {
    param([string]$Message)
    Write-Error $Message
    exit 1
}

function Assert-CommandExists {
    param(
        [string]$CommandName,
        [string]$InstallHint
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        Fail "$CommandName is required. $InstallHint"
    }
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$Arguments = @(),

        [string]$FailureMessage = "Native command failed."
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        Fail "$FailureMessage`nCommand: $FilePath $($Arguments -join ' ')`nExit code: $LASTEXITCODE"
    }
}

function Get-RepoRoot {
    param([string]$StartPath)

    $current = Split-Path -Parent $StartPath
    while ($current) {
        if (Test-Path -LiteralPath (Join-Path $current 'docker-compose.local.yml')) {
            return $current
        }

        $parent = Split-Path -Parent $current
        if ($parent -eq $current) {
            break
        }
        $current = $parent
    }

    Fail "Could not locate the repo root from $StartPath. Expected to find docker-compose.local.yml in an ancestor directory."
}

function Assert-PathExists {
    param(
        [string]$Path,
        [string]$Hint
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        Fail "Required path missing: $Path`n$Hint"
    }
}

function Ensure-FileFromExample {
    param(
        [string]$TargetPath,
        [string]$ExamplePath,
        [string]$Label
    )

    if (Test-Path -LiteralPath $TargetPath) {
        return
    }

    if (-not (Test-Path -LiteralPath $ExamplePath)) {
        Fail "Missing $Label and its example template was not found: $ExamplePath"
    }

    Copy-Item -LiteralPath $ExamplePath -Destination $TargetPath
    Write-Host "Created $Label from example: $TargetPath" -ForegroundColor Yellow
}

function Get-DotEnvValue {
    param(
        [string]$EnvFilePath,
        [string]$Key
    )

    if (-not (Test-Path -LiteralPath $EnvFilePath)) {
        return ''
    }

    $prefix = "$Key="
    foreach ($line in Get-Content -LiteralPath $EnvFilePath) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }
        if (-not $trimmed.StartsWith($prefix)) {
            continue
        }

        $value = $trimmed.Substring($prefix.Length).Trim()
        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        return $value
    }

    return ''
}

function Wait-ForHttpOk {
    param(
        [string]$Url,
        [int]$Attempts = 60,
        [int]$DelaySeconds = 2,
        [string]$SslHelp = ""
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return
            }
        } catch {
            $message = $_.Exception.Message
            if ($SslHelp -and ($message -match 'SSL|TLS|certificate|secure channel|trust relationship')) {
                Fail "$SslHelp`nLatest error: $message"
            }
            if ($attempt -eq $Attempts) {
                Fail "Timed out waiting for $Url`nLatest error: $message"
            }
        }

        Start-Sleep -Seconds $DelaySeconds
    }
}

function Get-ProcessExecutable {
    $current = Get-Process -Id $PID
    if ($current.Path) {
        return $current.Path
    }

    $pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue)
    if ($pwsh) {
        return $pwsh.Source
    }

    $powershell = (Get-Command powershell -ErrorAction SilentlyContinue)
    if ($powershell) {
        return $powershell.Source
    }

    Fail "Could not locate a PowerShell executable to launch the frontend dev server."
}

function Get-NpmExecutable {
    if ($IsWindows) {
        $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if ($npmCmd) {
            return $npmCmd.Source
        }
    }

    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($npm) {
        return $npm.Source
    }

    Fail "Could not locate npm on PATH."
}

function Get-InstallHint {
    param([string]$ToolName)

    switch ($ToolName) {
        'mkcert' {
            if ($IsMacOS) {
                return "Install it with `brew install mkcert` and then run `mkcert -install`."
            }
            if ($IsWindows) {
                return "Install it with `choco install mkcert -y` and then run `mkcert -install`."
            }
            return "Install it with your package manager, then run `mkcert -install`."
        }
        'docker' {
            if ($IsMacOS) {
                return "Install Docker Desktop for Mac and ensure `docker` is on PATH."
            }
            if ($IsWindows) {
                return "Install Docker Desktop and ensure `docker` is on PATH."
            }
            return "Install Docker and ensure `docker` is on PATH."
        }
        'npm' {
            if ($IsMacOS) {
                return "Install Node.js, for example with `brew install node`, and ensure `npm` is on PATH."
            }
            if ($IsWindows) {
                return "Install Node.js and ensure `npm` is on PATH."
            }
            return "Install Node.js and ensure `npm` is on PATH."
        }
        default {
            return "Install $ToolName and ensure it is on PATH."
        }
    }
}

function Test-FrontendDependencies {
    param([string]$FrontendDir)

    if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir 'node_modules'))) {
        Fail "frontend/node_modules is missing. Run `npm install` inside `frontend/` before using this script."
    }
}

function Test-ExtensionDependencies {
    param(
        [string]$ExtensionDir,
        [string]$FrontendDir
    )

    $extensionNodeModules = Test-Path -LiteralPath (Join-Path $ExtensionDir 'node_modules')
    $frontendNodeModules = Test-Path -LiteralPath (Join-Path $FrontendDir 'node_modules')

    if (-not $extensionNodeModules -and -not $frontendNodeModules) {
        Fail "Neither uah-browser-extension/node_modules nor frontend/node_modules exists. Run `npm install` in one of those directories before building the extension."
    }
}

function Start-FrontendWindow {
    param(
        [string]$FrontendDir,
        [string]$PowerShellExe
    )

    if ($IsWindows) {
        $command = "Set-Location -LiteralPath '$FrontendDir'; npm run dev:backend"
        Start-Process -FilePath $PowerShellExe -WorkingDirectory $FrontendDir -ArgumentList '-NoExit', '-Command', $command | Out-Null
        return
    }

    if ($IsMacOS -and (Get-Command osascript -ErrorAction SilentlyContinue)) {
        $escapedPath = $FrontendDir.Replace('\', '\\').Replace('"', '\"')
        $terminalCommand = "cd `"$escapedPath`"; npm run dev:backend"
        & osascript -e 'tell application "Terminal" to activate' -e "tell application `"Terminal`" to do script `"$terminalCommand`"" | Out-Null
        return
    }

    Fail "Automatic frontend launch in a new terminal window is only supported on Windows and macOS Terminal right now. Start `npm run dev:backend` manually in $FrontendDir or rerun with -SkipFrontend."
}

if ($BackendOnly) {
    $SkipFrontend = $true
    $SkipBuild = $true
}

$repoRoot = Get-RepoRoot -StartPath $PSCommandPath
$frontendDir = Join-Path $repoRoot 'frontend'
$extensionDir = Join-Path $repoRoot 'uah-browser-extension'
$localComposePath = Join-Path $repoRoot 'docker-compose.local.yml'
$rootEnvPath = Join-Path $repoRoot '.env'
$rootEnvExamplePath = Join-Path $repoRoot 'env-examples\local\.env.example'
$frontendEnvLocalPath = Join-Path $frontendDir '.env.local'
$frontendEnvLocalExamplePath = Join-Path $frontendDir '.env.local.example'
$extensionEnvLocalPath = Join-Path $extensionDir '.env.local'
$extensionEnvLocalExamplePath = Join-Path $extensionDir '.env.local.example'
$localCertDir = Join-Path $repoRoot 'volumes\certs\local'
$localCertPath = Join-Path $localCertDir 'tls.crt'
$localKeyPath = Join-Path $localCertDir 'tls.key'
$extensionDistPath = Join-Path $extensionDir 'dist'
$npmExecutable = Get-NpmExecutable

Write-Step "Checking prerequisites"
Assert-CommandExists -CommandName 'docker' -InstallHint (Get-InstallHint -ToolName 'docker')
Assert-CommandExists -CommandName 'npm' -InstallHint (Get-InstallHint -ToolName 'npm')
Assert-CommandExists -CommandName 'mkcert' -InstallHint (Get-InstallHint -ToolName 'mkcert')

Assert-PathExists -Path $localComposePath -Hint 'The local compose file is required to start backend-local.'
Ensure-FileFromExample -TargetPath $frontendEnvLocalPath -ExamplePath $frontendEnvLocalExamplePath -Label 'frontend/.env.local'
Ensure-FileFromExample -TargetPath $extensionEnvLocalPath -ExamplePath $extensionEnvLocalExamplePath -Label 'uah-browser-extension/.env.local'
Assert-PathExists -Path $rootEnvPath -Hint 'Create repo-root .env from env-examples/local/.env.example.'
Assert-PathExists -Path $rootEnvExamplePath -Hint 'The local root env example is missing from env-examples/local/.env.example.'
Assert-PathExists -Path $localCertPath -Hint 'Generate mkcert certs at volumes/certs/local/tls.crt and tls.key.'
Assert-PathExists -Path $localKeyPath -Hint 'Generate mkcert certs at volumes/certs/local/tls.crt and tls.key.'

Write-Step "Checking dependency directories"
Test-FrontendDependencies -FrontendDir $frontendDir
if (-not $SkipBuild) {
    Test-ExtensionDependencies -ExtensionDir $extensionDir -FrontendDir $frontendDir
}

Write-Step "Starting local backend"
Push-Location $repoRoot
try {
    Invoke-NativeCommand `
        -FilePath 'docker' `
        -Arguments @('compose', '-f', $localComposePath, '--profile', 'backend', 'up', '-d', 'db-local', 'backend-local') `
        -FailureMessage 'Failed to start the local backend with docker compose.'
} finally {
    Pop-Location
}

Write-Host "Waiting for backend-local to answer on http://localhost:8000/openapi.json ..."
Wait-ForHttpOk -Url 'http://localhost:8000/openapi.json' -Attempts 60 -DelaySeconds 2
Write-Host "Backend is ready." -ForegroundColor Green

if (-not $SkipFrontend) {
    Write-Step "Starting HTTPS frontend"
    $frontendAlreadyRunning = $false
    try {
        Wait-ForHttpOk -Url 'https://localhost:5173/' -Attempts 1 -DelaySeconds 1 -SslHelp ''
        $frontendAlreadyRunning = $true
    } catch {
        $frontendAlreadyRunning = $false
    }

    if ($frontendAlreadyRunning) {
        Write-Host "Frontend already appears to be running on https://localhost:5173." -ForegroundColor Yellow
    } else {
        $powerShellExe = Get-ProcessExecutable
        Start-FrontendWindow -FrontendDir $frontendDir -PowerShellExe $powerShellExe
    }

    Write-Host "Waiting for HTTPS frontend on https://localhost:5173 ..."
    Wait-ForHttpOk `
        -Url 'https://localhost:5173/' `
        -Attempts 60 `
        -DelaySeconds 2 `
        -SslHelp 'The HTTPS frontend could not be reached because the localhost certificate is not trusted. Open https://localhost:5173 in Chrome, trust the mkcert certificate if prompted, then rerun this script.'

    Write-Host "Frontend is ready." -ForegroundColor Green
} else {
    Write-Step "Skipping frontend startup"
}

if (-not $SkipBuild) {
    Write-Step "Building the browser extension"
    if (Test-Path -LiteralPath $extensionDistPath) {
        Remove-Item -LiteralPath $extensionDistPath -Recurse -Force
    }

    Push-Location $extensionDir
    try {
        Invoke-NativeCommand `
            -FilePath $npmExecutable `
            -Arguments @('run', 'build') `
            -FailureMessage 'Browser extension build failed.'
    } finally {
        Pop-Location
    }

    if (-not (Test-Path -LiteralPath $extensionDistPath)) {
        Fail "Extension build finished without producing $extensionDistPath"
    }

    Write-Host "Extension build is ready at $extensionDistPath" -ForegroundColor Green
} else {
    Write-Step "Skipping extension build"
}

Write-Step "Next test steps"
Write-Host "1. Open Chrome and go to chrome://extensions"
Write-Host "2. Turn on Developer mode"
if (-not $SkipBuild) {
    Write-Host "3. Click Load unpacked and choose: $extensionDistPath"
} else {
    Write-Host "3. Load the existing unpacked extension from: $extensionDistPath"
}
Write-Host "4. Open the extension popup and sign in with email/password"
Write-Host "5. Verify popup close/reopen keeps the session"
Write-Host "6. Verify Profiles loads and detail copy buttons work"
Write-Host "7. Verify Resumes loads and detail copy buttons work"
Write-Host "8. Verify Open UAH opens https://localhost:5173"
Write-Host "9. Verify logout clears extension state"
Write-Host ""
Write-Host "Local harness note: Google OAuth is intentionally disabled on localhost." -ForegroundColor Yellow
Write-Host "Seeded login env file: $rootEnvPath" -ForegroundColor Yellow
Write-Host "Extension local config env file: $extensionEnvLocalPath" -ForegroundColor Yellow

$devAuthEnabled = (Get-DotEnvValue -EnvFilePath $rootEnvPath -Key 'DEV_AUTH_TEST_ACCOUNT_ENABLED').ToLowerInvariant()
if ($devAuthEnabled -in @('true', '1', 'yes', 'on')) {
    $devAuthEmail = Get-DotEnvValue -EnvFilePath $rootEnvPath -Key 'DEV_AUTH_TEST_EMAIL'
    if (-not $devAuthEmail) {
        $devAuthEmail = Get-DotEnvValue -EnvFilePath $rootEnvPath -Key 'DEV_AUTH_TEST_USERNAME'
    }
    $devAuthPassword = Get-DotEnvValue -EnvFilePath $rootEnvPath -Key 'DEV_AUTH_TEST_PASSWORD'

    Write-Host "Seeded local login:" -ForegroundColor Yellow
    Write-Host "  Email/username: $devAuthEmail" -ForegroundColor Yellow
    Write-Host "  Password: $devAuthPassword" -ForegroundColor Yellow
} else {
    Write-Host "If you enable DEV_AUTH_TEST_ACCOUNT_ENABLED in $rootEnvPath, the script will print that seeded account for login." -ForegroundColor Yellow
}
