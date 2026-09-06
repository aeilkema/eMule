[CmdletBinding()]
param(
    [switch]$BuildMsi,
    [switch]$DesktopShortcut,
    [string]$WixExe = "wix"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$Artifacts = Join-Path $RepoRoot "artifacts"
$Exe = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-x64.exe"
$Zip = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-x64-portable.zip"
$Msi = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-x64.msi"
$RcManifest = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-RC-MANIFEST.txt"
$Acceptance = Join-Path $Artifacts "preview2-runtime-acceptance.json"
$AcceptanceHarness = Join-Path $RepoRoot "preview2-runtime-acceptance.ps1"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) {
    throw "Preview 2 executable missing: $Exe. Run .\build-local.ps1 -KeepActivationStage first."
}
if (-not (Test-Path -LiteralPath $AcceptanceHarness -PathType Leaf)) {
    throw "Preview 2 runtime acceptance harness missing: $AcceptanceHarness"
}

Write-Host "[1/5] Verifying build-bound core runtime acceptance..."
& $AcceptanceHarness -VerifyCore
if ($LASTEXITCODE -ne 0) { throw "Preview 2 core runtime acceptance is not PASS." }
if (-not (Test-Path -LiteralPath $Acceptance -PathType Leaf)) {
    throw "Preview 2 acceptance record missing after verification: $Acceptance"
}

Write-Host "[2/5] Verifying release layout..."
& (Join-Path $RepoRoot "verify-preview2-release.ps1") -RequireBuiltExe
if ($LASTEXITCODE -ne 0) { throw "Preview 2 release layout verification failed." }

Write-Host "[3/5] Building portable package..."
& (Join-Path $RepoRoot "package-preview2.ps1")
if ($LASTEXITCODE -ne 0) { throw "Preview 2 portable packaging failed." }
if (-not (Test-Path -LiteralPath $Zip -PathType Leaf)) {
    throw "Preview 2 portable package was not created: $Zip"
}

$msiStatus = "not requested"
if ($BuildMsi) {
    Write-Host "[4/5] Building MSI..."
    $args = @("-WixExe", $WixExe)
    if ($DesktopShortcut) { $args += "-DesktopShortcut" }
    & (Join-Path $RepoRoot "build-preview2-installer.ps1") @args
    if ($LASTEXITCODE -ne 0) { throw "Preview 2 MSI build failed." }
    if (-not (Test-Path -LiteralPath $Msi -PathType Leaf)) {
        throw "Preview 2 MSI was not created: $Msi"
    }
    $msiStatus = "built"
}
else {
    Write-Host "[4/5] MSI skipped (use -BuildMsi to include it)."
}

Write-Host "[5/5] Writing RC manifest..."
$head = (& git -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($head)) {
    throw "Unable to resolve Git HEAD for RC manifest."
}

$entries = New-Object System.Collections.Generic.List[string]
$entries.Add("eMule Next 0.2.0 Preview 2 - Release Candidate Manifest")
$entries.Add("Generated: $([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss zzz'))")
$entries.Add("Git head: $head")
$entries.Add("MSI: $msiStatus")
$entries.Add("Core runtime acceptance: PASS")
$entries.Add("")

foreach ($file in @($Exe, $Zip, $Acceptance)) {
    $hash = Get-FileHash -LiteralPath $file -Algorithm SHA256
    $entries.Add(("{0}  {1}" -f $hash.Hash.ToLowerInvariant(), (Split-Path -Leaf $file)))
}
if ($BuildMsi -and (Test-Path -LiteralPath $Msi -PathType Leaf)) {
    $hash = Get-FileHash -LiteralPath $Msi -Algorithm SHA256
    $entries.Add(("{0}  {1}" -f $hash.Hash.ToLowerInvariant(), (Split-Path -Leaf $Msi)))
}

$entries.Add("")
$entries.Add("Core runtime acceptance is bound to this Git head and executable SHA256.")
$entries.Add("Package acceptance remains separate until PORTABLE/MSI checks in preview2-runtime-acceptance.json are PASS.")
$entries.Add("Use .\preview2-runtime-acceptance.ps1 -VerifyAll before calling the complete package set release-ready.")

[System.IO.File]::WriteAllLines($RcManifest, [string[]]$entries, $Utf8NoBom)
Write-Host "PREVIEW 2 RC ARTIFACT FINALIZATION SUCCESS"
Write-Host "Manifest: $RcManifest"
