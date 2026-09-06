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
    "finalize-preview2-rc.ps1",
    "create-preview2-support-bundle.ps1",
    "installer\preview2\Product.wxs",
    "docs\EMULE_NEXT_PREVIEW2_RELEASE_NOTES.md",
    "docs\EMULE_NEXT_RUNTIME_TEST_MATRIX.md",
    "docs\EMULE_NEXT_TODO.md",
    "docs\EMULE_NEXT_PROJECT_PLAN.md",
    "tools\emule-next\activate-features.py",
    "tools\emule-next\activate-preview2.py",
    "tools\emule-next\activate-preview2-ux-completion.py",
    "tools\emule-next\activate-preview2-settings-complete.py",
    "tools\emule-next\activate-preview2-settings-complete-hardening.py",
    "tools\emule-next\activate-preview2-search-ux.py",
    "tools\emule-next\activate-preview2-header-status.py",
    "tools\emule-next\activate-preview2-legacy-theme-routing.py",
    "tools\emule-next\activate-preview2-theme-coverage.py",
    "tools\emule-next\activate-preview2-warning-cleanup-dashboard.py",
    "tools\emule-next\activate-preview2-warning-cleanup-intelligence.py",
    "tools\emule-next\activate-preview2-warning-cleanup-kad.py",
    "tools\emule-next\activate-preview2-warning-cleanup-shared.py",
    "tools\emule-next\activate-preview2-warning-cleanup-mfc.py",
    "tools\emule-next\activate-preview2-warning-cleanup-main.py",
    "tools\emule-next\activate-preview2-dashboard-ux.py",
    "tools\emule-next\activate-preview2-dashboard-compile-hardening.py",
    "tools\emule-next\verify-preview2-activation-chain.py",
    "tools\emule-next\verify-preview2-warning-cleanup.py",
    "tools\emule-next\verify-preview2-settings-theme.py",
    "tools\emule-next\verify-preview2-ux-completion.py",
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
    'python (Join-Path $tools "activate-features.py")',
    '$ReleaseVerifier = Join-Path $RepoRoot "verify-preview2-release.ps1"',
    '& $ReleaseVerifier',
    '& $ReleaseVerifier -RequireBuiltExe',
    'Preview 2:'
)) {
    if (-not $build.Contains($marker)) {
        throw "Preview 2 release verification: build-local.ps1 missing '$marker'"
    }
}

$preflightPos = $build.IndexOf('& $ReleaseVerifier')
$stagePos = $build.IndexOf('$StageA = New-CleanActivationStage')
if ($preflightPos -lt 0 -or $stagePos -lt 0 -or $preflightPos -gt $stagePos) {
    throw "Preview 2 release verification: repository preflight must run before activation-stage creation"
}

$activationGatePath = Join-Path $RepoRoot "tools\emule-next\verify-preview2-activation-chain.py"
python $activationGatePath
if ($LASTEXITCODE -ne 0) {
    throw "Preview 2 release verification: structural activation-chain gate failed"
}

$orchestrator = Get-Content -LiteralPath (Join-Path $RepoRoot "tools\emule-next\activate-preview2.py") -Raw
foreach ($marker in @(
    'activate-preview2-main-shell.py',
    'activate-preview2-ux-completion.py',
    'activate-preview2-settings-complete.py',
    'activate-preview2-settings-complete-hardening.py',
    'activate-preview2-search-ux.py',
    'activate-preview2-header-status.py',
    'activate-preview2-legacy-theme-routing.py',
    'activate-preview2-theme-coverage.py',
    'activate-preview2-warning-cleanup-dashboard.py',
    'activate-preview2-warning-cleanup-intelligence.py',
    'activate-preview2-warning-cleanup-kad.py',
    'activate-preview2-warning-cleanup-shared.py',
    'activate-preview2-warning-cleanup-mfc.py',
    'activate-preview2-warning-cleanup-main.py',
    'activate-preview2-dashboard-ux.py',
    'activate-preview2-dashboard-compile-hardening.py',
    'verify-preview2-activation-chain.py',
    'verify-preview2-warning-cleanup.py',
    'verify-preview2-settings-theme.py',
    'verify-preview2-ux-completion.py',
    'verify-preview2-product.py'
)) {
    if (-not $orchestrator.Contains($marker)) {
        throw "Preview 2 release verification: product materialization missing '$marker'"
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
foreach ($forbidden in @('preferences.ini', 'known.met', '.part.met', 'emule-next.sqlite')) {
    if ($portable -match ('(?im)^\s*Copy-Item[^\r\n]*' + [regex]::Escape($forbidden))) {
        throw "Preview 2 release verification: portable packaging appears to copy user data '$forbidden'"
    }
}
if (-not $portable.Contains('create-preview2-support-bundle.ps1')) {
    throw "Preview 2 release verification: portable package does not include safe support helper"
}

$support = Get-Content -LiteralPath (Join-Path $RepoRoot "create-preview2-support-bundle.ps1") -Raw
if ($support -match '(?im)^\s*Copy-Item[^\r\n]*(?:config|known\.met|\.part(?:\.met)?|sqlite)') {
    throw "Preview 2 release verification: support helper contains a user-state Copy-Item command"
}
foreach ($privacyMarker in @(
    'no intelligence SQLite database',
    'no preferences/config files',
    'no peer history or known.met',
    'no incomplete download .part/.part.met files'
)) {
    if (-not $support.Contains($privacyMarker)) {
        throw "Preview 2 release verification: support helper missing privacy contract '$privacyMarker'"
    }
}

$finalizer = Get-Content -LiteralPath (Join-Path $RepoRoot "finalize-preview2-rc.ps1") -Raw
foreach ($marker in @(
    'verify-preview2-release.ps1',
    'package-preview2.ps1',
    'build-preview2-installer.ps1',
    'RC-MANIFEST',
    'Runtime acceptance remains separate from artifact creation'
)) {
    if (-not $finalizer.Contains($marker)) {
        throw "Preview 2 release verification: RC finalizer missing '$marker'"
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
