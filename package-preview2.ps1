[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$Artifacts = Join-Path $RepoRoot "artifacts"
$PreviewExe = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-x64.exe"
$Stage = Join-Path $Artifacts "preview2-portable"
$Zip = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-x64-portable.zip"
$Manifest = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-SHA256.txt"

if (-not (Test-Path -LiteralPath $PreviewExe -PathType Leaf)) {
    throw "Preview 2 executable not found: $PreviewExe. Run .\build-local.ps1 first."
}

if (Test-Path -LiteralPath $Stage) {
    Remove-Item -LiteralPath $Stage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

Copy-Item -LiteralPath $PreviewExe -Destination (Join-Path $Stage "eMule-Next.exe") -Force
if (Test-Path -LiteralPath (Join-Path $RepoRoot "docs\EMULE_NEXT_RUNTIME_TEST_MATRIX.md")) {
    Copy-Item -LiteralPath (Join-Path $RepoRoot "docs\EMULE_NEXT_RUNTIME_TEST_MATRIX.md") -Destination (Join-Path $Stage "RUNTIME-TEST-MATRIX.md") -Force
}
if (Test-Path -LiteralPath (Join-Path $RepoRoot "docs\EMULE_NEXT_PREVIEW2_RELEASE_NOTES.md")) {
    Copy-Item -LiteralPath (Join-Path $RepoRoot "docs\EMULE_NEXT_PREVIEW2_RELEASE_NOTES.md") -Destination (Join-Path $Stage "RELEASE-NOTES.md") -Force
}
if (Test-Path -LiteralPath (Join-Path $RepoRoot "create-preview2-support-bundle.ps1")) {
    Copy-Item -LiteralPath (Join-Path $RepoRoot "create-preview2-support-bundle.ps1") -Destination (Join-Path $Stage "create-support-bundle.ps1") -Force
}

$readme = @"
eMule Next 0.2.0 Preview 2 (x64)
================================

This package contains the Preview 2 executable plus release/test documentation
and a safe support-bundle helper. It deliberately contains no user configuration,
intelligence database, download state or peer history. Existing user data is
therefore never overwritten by unpacking this ZIP.

Important safety defaults:
- Smart Scheduling starts in Analysis only unless the existing user profile explicitly says otherwise.
- eD2K/Kad protocol behavior remains the upstream eMule v0.72a core.
- Intelligence/database failure is designed not to block the legacy networking core.

Use Diagnostics for database health, backups, the stress self-test and the runtime validation matrix.
After exporting a Diagnostics report, create-support-bundle.ps1 can create a privacy-bounded ZIP
containing only that report, build identity and public release/test documentation.
"@
Set-Content -LiteralPath (Join-Path $Stage "README-PREVIEW2.txt") -Value $readme -Encoding utf8

if (Test-Path -LiteralPath $Zip) {
    Remove-Item -LiteralPath $Zip -Force
}
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $Zip -CompressionLevel Optimal

$files = @($PreviewExe, $Zip)
$lines = foreach ($file in $files) {
    $hash = Get-FileHash -LiteralPath $file -Algorithm SHA256
    "{0}  {1}" -f $hash.Hash.ToLowerInvariant(), (Split-Path -Leaf $file)
}
Set-Content -LiteralPath $Manifest -Value $lines -Encoding ascii

Write-Host "PORTABLE PACKAGE SUCCESS"
Write-Host "ZIP: $Zip"
Write-Host "SHA256: $Manifest"
