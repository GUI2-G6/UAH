[CmdletBinding()]
param(
    [switch]$SkipBuild,
    [switch]$SkipFrontend,
    [switch]$BackendOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $PSCommandPath
$scriptPath = Join-Path $scriptDir 'local-extension-test.ps1'

& $scriptPath -ExtensionTarget 'beta' -SkipBuild:$SkipBuild -SkipFrontend:$SkipFrontend -BackendOnly:$BackendOnly
$exitCodeVar = Get-Variable -Name LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue
if ($null -ne $exitCodeVar) {
    exit $exitCodeVar.Value
}
exit 0
