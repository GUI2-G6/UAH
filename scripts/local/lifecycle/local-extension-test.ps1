[CmdletBinding()]
param(
    [ValidateSet('local', 'beta')]
    [string]$ExtensionTarget = 'local',

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

function Normalize-EnvNamespace {
    param([string]$Value)

    return [regex]::Replace(([string]$Value).Trim().ToLowerInvariant(), '[^a-z0-9_.-]', '_')
}

function Get-ExtensionAuthCookieName {
    param([string]$EnvFilePath)

    $explicitCookieName = Get-DotEnvValue -EnvFilePath $EnvFilePath -Key 'VITE_EXTENSION_AUTH_COOKIE_NAME'
    if ($explicitCookieName) {
        return $explicitCookieName
    }

    $namespace = Normalize-EnvNamespace (Get-DotEnvValue -EnvFilePath $EnvFilePath -Key 'VITE_EXTENSION_AUTH_NAMESPACE')
    if ($namespace) {
        return "uah_auth_$namespace"
    }

    return ''
}

function Test-LocalhostOrigin {
    param([string]$Origin)

    if (-not $Origin) {
        return $false
    }

    try {
        $uri = [System.Uri]$Origin
        return $uri.Host.ToLowerInvariant() -eq 'localhost'
    } catch {
        return $false
    }
}

function Assert-ExtensionTargetConfig {
    param(
        [string]$Target,
        [string]$EnvFilePath
    )

    $appOrigin = Get-DotEnvValue -EnvFilePath $EnvFilePath -Key 'VITE_EXTENSION_APP_ORIGIN'
    $apiOrigin = Get-DotEnvValue -EnvFilePath $EnvFilePath -Key 'VITE_EXTENSION_API_ORIGIN'
    $authCookieName = Get-ExtensionAuthCookieName -EnvFilePath $EnvFilePath

    if (-not $appOrigin) {
        Fail "VITE_EXTENSION_APP_ORIGIN is missing from $EnvFilePath"
    }
    if (-not $apiOrigin) {
        Fail "VITE_EXTENSION_API_ORIGIN is missing from $EnvFilePath"
    }
    if (-not $authCookieName) {
        Fail "Set VITE_EXTENSION_AUTH_COOKIE_NAME or VITE_EXTENSION_AUTH_NAMESPACE in $EnvFilePath"
    }

    if ($Target -eq 'beta') {
        if ((Test-LocalhostOrigin -Origin $appOrigin) -or (Test-LocalhostOrigin -Origin $apiOrigin)) {
            Fail "Beta extension mode must not point at localhost. Update $EnvFilePath to beta HTTPS origins."
        }
    }

    return @{
        AppOrigin = $appOrigin
        ApiOrigin = $apiOrigin
        AuthCookieName = $authCookieName
        GoogleOAuthEnabled = -not ((Test-LocalhostOrigin -Origin $appOrigin) -and (Test-LocalhostOrigin -Origin $apiOrigin))
    }
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
    if ($ExtensionTarget -ne 'local') {
        Fail "-BackendOnly is only supported when -ExtensionTarget local is selected."
    }
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
$extensionEnvPath = Join-Path $extensionDir '.env'
$extensionEnvLocalPath = Join-Path $extensionDir '.env.local'
$extensionEnvLocalExamplePath = Join-Path $extensionDir '.env.local.example'
$localCertDir = Join-Path $repoRoot 'volumes\certs\local'
$localCertPath = Join-Path $localCertDir 'tls.crt'
$localKeyPath = Join-Path $localCertDir 'tls.key'
$extensionDistPath = Join-Path $extensionDir 'dist'
$npmExecutable = Get-NpmExecutable
$selectedExtensionEnvPath = if ($ExtensionTarget -eq 'beta') { $extensionEnvPath } else { $extensionEnvLocalPath }

Write-Step "Checking prerequisites"
Assert-CommandExists -CommandName 'npm' -InstallHint (Get-InstallHint -ToolName 'npm')

if ($ExtensionTarget -eq 'local') {
    Assert-CommandExists -CommandName 'docker' -InstallHint (Get-InstallHint -ToolName 'docker')
    Assert-CommandExists -CommandName 'mkcert' -InstallHint (Get-InstallHint -ToolName 'mkcert')

    Assert-PathExists -Path $localComposePath -Hint 'The local compose file is required to start backend-local.'
    Ensure-FileFromExample -TargetPath $frontendEnvLocalPath -ExamplePath $frontendEnvLocalExamplePath -Label 'frontend/.env.local'
    Ensure-FileFromExample -TargetPath $extensionEnvLocalPath -ExamplePath $extensionEnvLocalExamplePath -Label 'uah-browser-extension/.env.local'
    Assert-PathExists -Path $rootEnvPath -Hint 'Create repo-root .env from env-examples/local/.env.example.'
    Assert-PathExists -Path $rootEnvExamplePath -Hint 'The local root env example is missing from env-examples/local/.env.example.'
    Assert-PathExists -Path $localCertPath -Hint 'Generate mkcert certs at volumes/certs/local/tls.crt and tls.key.'
    Assert-PathExists -Path $localKeyPath -Hint 'Generate mkcert certs at volumes/certs/local/tls.crt and tls.key.'
} else {
    Assert-PathExists -Path $extensionEnvPath -Hint 'Create uah-browser-extension/.env with the beta HTTPS origins and auth namespace before building for beta.'
}

$selectedExtensionAppOrigin = Get-DotEnvValue -EnvFilePath $selectedExtensionEnvPath -Key 'VITE_EXTENSION_APP_ORIGIN'
$extensionTargetConfig = Assert-ExtensionTargetConfig -Target $ExtensionTarget -EnvFilePath $selectedExtensionEnvPath

Write-Step "Checking dependency directories"
if ($ExtensionTarget -eq 'local') {
    Test-FrontendDependencies -FrontendDir $frontendDir
}
if (-not $SkipBuild) {
    Test-ExtensionDependencies -ExtensionDir $extensionDir -FrontendDir $frontendDir
}

if ($ExtensionTarget -eq 'local') {
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
} else {
    Write-Step "Skipping local stack startup"
    Write-Host "Extension target '$ExtensionTarget' uses $selectedExtensionEnvPath" -ForegroundColor Yellow
}

if (-not $SkipBuild) {
    Write-Step "Building the browser extension"
    if (Test-Path -LiteralPath $extensionDistPath) {
        Remove-Item -LiteralPath $extensionDistPath -Recurse -Force
    }

    Push-Location $extensionDir
    try {
        $previousSelectedEnvFile = $env:UAH_EXTENSION_ENV_FILE
        $env:UAH_EXTENSION_ENV_FILE = $selectedExtensionEnvPath
        Invoke-NativeCommand `
            -FilePath $npmExecutable `
            -Arguments @('run', 'build') `
            -FailureMessage 'Browser extension build failed.'
    } finally {
        if ($null -eq $previousSelectedEnvFile) {
            Remove-Item Env:UAH_EXTENSION_ENV_FILE -ErrorAction SilentlyContinue
        } else {
            $env:UAH_EXTENSION_ENV_FILE = $previousSelectedEnvFile
        }
        Pop-Location
    }

    if (-not (Test-Path -LiteralPath $extensionDistPath)) {
        Fail "Extension build finished without producing $extensionDistPath"
    }

    $manifestPath = Join-Path $extensionDistPath 'manifest.json'
    Assert-PathExists -Path $manifestPath -Hint 'Extension build did not emit dist/manifest.json.'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $expectedHostPermission = "$($extensionTargetConfig.ApiOrigin)/*"
    $actualHostPermissions = @($manifest.host_permissions)
    if ($expectedHostPermission -notin $actualHostPermissions) {
        Fail "Built extension manifest does not include expected host permission '$expectedHostPermission'."
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
Write-Host "8. Verify Open UAH opens $selectedExtensionAppOrigin"
Write-Host "9. Verify logout clears extension state"
Write-Host ""
Write-Host "Extension target: $ExtensionTarget" -ForegroundColor Yellow
Write-Host "Extension build env file: $selectedExtensionEnvPath" -ForegroundColor Yellow
Write-Host "Extension app origin: $($extensionTargetConfig.AppOrigin)" -ForegroundColor Yellow
Write-Host "Extension API origin: $($extensionTargetConfig.ApiOrigin)" -ForegroundColor Yellow
Write-Host "Extension auth cookie: $($extensionTargetConfig.AuthCookieName)" -ForegroundColor Yellow

if ($ExtensionTarget -eq 'local') {
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
} else {
    Write-Host "Beta note: this script does not start local backend/frontend when -ExtensionTarget beta is selected." -ForegroundColor Yellow
    if ($extensionTargetConfig.GoogleOAuthEnabled) {
        Write-Host "Google OAuth is enabled for this build. The popup should show 'Continue with Google' and read the '$($extensionTargetConfig.AuthCookieName)' cookie from $($extensionTargetConfig.ApiOrigin)." -ForegroundColor Yellow
    } else {
        Write-Host "Google OAuth is disabled for this build because both configured origins resolve to localhost." -ForegroundColor Yellow
    }
}
