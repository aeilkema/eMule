[CmdletBinding()]
param(
    [switch]$RequireBuiltExe
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$requiredFiles = @(
    "build-local.ps1",
    "package-preview2.ps1",
    "build-preview2-installer.ps1",
    "installer\preview2\Product.wxs",
    "docs\EMULE_NEXT_PREVIEW2_RELEASE_NOTES.md",
    "docs\EMULE_NEXT_RUNTIME_TEST_MATRIX.md",
    "tools\emule-next\activate-preview2.py",
    "tools\emule-next\verify-preview2-product.py"
)

foreach ($relative in $requiredFiles) {
    $path = Join-Path $RepoRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Preview 2 release verification: missing $relative"
    }
}

$build = Get-Content -LiteralPath (Join-Path $RepoRoot "build-local.ps1") -Raw
foreach ($marker in @(
    'eMule-Next-0.2.0-Preview2-x64.exe',
    'Building eMule Next Preview 2 x64',
    'Preview 2:'
)) {
    if (-not $build.Contains($marker)) {
        throw "Preview 2 release verification: build-local.ps1 missing '$marker'"
    }
}

$wix = Get-Content -LiteralPath (Join-Path $RepoRoot "installer\preview2\Product.wxs") -Raw
foreach ($marker in @(
    'Version="0.2.0"',
    '<MajorUpgrade',
    'ProgramFiles64Folder',
    'StartMenuShortcut',
    '$(var.PreviewExe)'
)) {
    if (-not $wix.Contains($marker)) {
        throw "Preview 2 release verification: MSI definition missing '$marker'"
    }
}
if ($wix.Contains('AppDataFolder') -or $wix.Contains('LocalAppDataFolder') -or $wix.Contains('CommonAppDataFolder')) {
    throw "Preview 2 release verification: MSI must not own user-data directories"
}

$portable = Get-Content -LiteralPath (Join-Path $RepoRoot "package-preview2.ps1") -Raw
foreach ($forbidden in @('config', 'preferences.ini', 'known.met', '.part.met')) {
    if ($portable -match [regex]::Escape("Copy-Item") + '.*' + [regex]::Escape($forbidden)) {
        throw "Preview 2 release verification: portable packaging appears to copy user data '$forbidden'"
    }
}

if ($RequireBuiltExe) {
    $exe = Join-Path $RepoRoot "artifacts\eMule-Next-0.2.0-Preview2-x64.exe"
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "Preview 2 release verification: built executable missing: $exe"
    }
    $hash = Get-FileHash -LiteralPath $exe -Algorithm SHA256
    Write-Host "Preview 2 executable SHA256: $($hash.Hash.ToLowerInvariant())"
}

Write-Host "Preview 2 release layout verification passed"
