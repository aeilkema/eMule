[CmdletBinding()]
param(
    [switch]$RebuildDependencies,
    [switch]$KeepActivationStage
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

$MSBuild = "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\MSBuild.exe"
$PreviewExeName = "eMule-Next-0.1.0-Preview1-x64.exe"
$LatestExeName = "eMule-Next-x64.exe"
$StageRoot = Join-Path $RepoRoot "build\activation-stage"
$StageSource = Join-Path $StageRoot "srchybrid"
$StageTools = Join-Path $StageRoot "tools\emule-next"

if (-not (Test-Path $MSBuild)) {
    throw "Visual Studio 2026 Build Tools MSBuild niet gevonden: $MSBuild"
}

# Feature activators deliberately edit their overlay. Run them on an isolated
# copy so a build can never dirty C:\Projects\eMule\srchybrid. The activated,
# verified staging overlay is copied over the generated upstream tree later.
if (Test-Path -LiteralPath $StageRoot) {
    Remove-Item -LiteralPath $StageRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $StageSource | Out-Null
New-Item -ItemType Directory -Force -Path $StageTools | Out-Null

Write-Host "Preparing isolated eMule Next activation overlay..."
Get-ChildItem -LiteralPath (Join-Path $RepoRoot "srchybrid") -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $StageSource -Recurse -Force
}
Get-ChildItem -LiteralPath (Join-Path $RepoRoot "tools\emule-next") -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $StageTools -Recurse -Force
}

Write-Host "Applying eMule Next integration in staging..."
python (Join-Path $StageTools "integrate.py")
if ($LASTEXITCODE -ne 0) {
    throw "Integration failed in isolated staging overlay: $StageRoot"
}

Write-Host "Activating eMule Next runtime features in staging..."
python (Join-Path $StageTools "activate-features.py")
if ($LASTEXITCODE -ne 0) {
    throw "Feature activation failed in isolated staging overlay: $StageRoot"
}

Write-Host "Verifying activation idempotence in staging..."
python (Join-Path $StageTools "verify-activation-idempotence.py")
if ($LASTEXITCODE -ne 0) {
    throw "Feature activation is not idempotent. Inspect the staging overlay at $StageRoot"
}

$SourceDir = Join-Path $RepoRoot "build\upstream-v0.72a\eMule0.72a-Sources\srchybrid"

if ($RebuildDependencies -or -not (Test-Path "$SourceDir\emule.vcxproj")) {
    Write-Host "Bootstrapping complete source tree..."
    $lines = & .\tools\emule-next\bootstrap-source.ps1 -SkipIntegration
    if ($LASTEXITCODE -ne 0) {
        throw "Bootstrap failed."
    }

    $SourceDir = ($lines | Select-Object -Last 1).Trim()

    Write-Host "Building dependencies..."
    & .\tools\emule-next\build-dependencies.ps1 `
        -SourceDir $SourceDir `
        -MSBuildExe $MSBuild `
        -Configuration Release `
        -Platform x64 `
        -PlatformToolset v145

    if ($LASTEXITCODE -ne 0) {
        throw "Dependency build failed."
    }
}

if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
    throw "Generated eMule source directory not found: $SourceDir"
}

# Apply only the fully activated and second-pass-verified staging overlay.
Get-ChildItem -LiteralPath $StageSource -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $SourceDir -Recurse -Force
}

Write-Host "Building eMule Next Preview 1 x64..."

& $MSBuild `
    "$SourceDir\emule.vcxproj" `
    /m `
    /t:Build `
    /p:BuildProjectReferences=false `
    /p:Configuration=Release `
    /p:Platform=x64 `
    /p:PlatformToolset=v145 `
    /p:WindowsTargetPlatformVersion=10.0 `
    /verbosity:minimal

if ($LASTEXITCODE -ne 0) {
    throw "eMule build failed. Activated staging overlay kept at $StageRoot for diagnosis."
}

$Exe = Join-Path $SourceDir "x64\Release\emule.exe"

if (-not (Test-Path $Exe)) {
    throw "Build succeeded but emule.exe was not found."
}

$Artifacts = Join-Path $RepoRoot "artifacts"
New-Item -ItemType Directory -Force $Artifacts | Out-Null

$PreviewExe = Join-Path $Artifacts $PreviewExeName
$LatestExe = Join-Path $Artifacts $LatestExeName
Copy-Item $Exe $PreviewExe -Force
Copy-Item $Exe $LatestExe -Force

Get-FileHash $PreviewExe -Algorithm SHA256

if (-not $KeepActivationStage -and (Test-Path -LiteralPath $StageRoot)) {
    Remove-Item -LiteralPath $StageRoot -Recurse -Force
}

Write-Host ""
Write-Host "SUCCESS"
Write-Host "Preview: $PreviewExe"
Write-Host "Latest alias: $LatestExe"
Write-Host "Repository overlay was not modified by integration/activation."