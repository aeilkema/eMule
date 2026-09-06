[CmdletBinding()]
param(
    [switch]$RebuildDependencies,
    [switch]$KeepActivationStage,
    [switch]$ActivationOnly
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

$MSBuild = "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\MSBuild.exe"
$PreviewExeName = "eMule-Next-0.1.0-Preview1-x64.exe"
$LatestExeName = "eMule-Next-x64.exe"
$StageRoot = Join-Path $RepoRoot "build\activation-stage"
$VerifyStageRoot = Join-Path $RepoRoot "build\activation-stage-verify"

if (-not $ActivationOnly -and -not (Test-Path $MSBuild)) {
    throw "Visual Studio 2026 Build Tools MSBuild niet gevonden: $MSBuild"
}

function Remove-StageIfPresent([string]$Root) {
    if (Test-Path -LiteralPath $Root) {
        Remove-Item -LiteralPath $Root -Recurse -Force
    }
}

function New-CleanActivationStage([string]$Root, [string]$Label) {
    $source = Join-Path $Root "srchybrid"
    $tools = Join-Path $Root "tools\emule-next"

    Remove-StageIfPresent $Root
    New-Item -ItemType Directory -Force -Path $source | Out-Null
    New-Item -ItemType Directory -Force -Path $tools | Out-Null

    Write-Host "Preparing clean eMule Next activation overlay ($Label)..."
    Get-ChildItem -LiteralPath (Join-Path $RepoRoot "srchybrid") -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $source -Recurse -Force
    }
    Get-ChildItem -LiteralPath (Join-Path $RepoRoot "tools\emule-next") -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $tools -Recurse -Force
    }

    return @{
        Root = $Root
        Source = $source
        Tools = $tools
        Label = $Label
    }
}

function Invoke-CleanActivation([hashtable]$Stage) {
    $root = $Stage.Root
    $source = $Stage.Source
    $tools = $Stage.Tools
    $label = $Stage.Label

    Write-Host "Applying eMule Next integration ($label)..."
    python (Join-Path $tools "integrate.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Integration failed in clean activation overlay ($label): $root"
    }

    # Git for Windows can materialize repository text as CRLF even when the blob
    # is LF. Normalize only the isolated stage so multiline activator anchors are
    # deterministic. The real checkout is never modified.
    Write-Host "Normalizing activation-stage source newlines ($label)..."
    python (Join-Path $tools "normalize-stage-newlines.py") $source
    if ($LASTEXITCODE -ne 0) {
        throw "Activation-stage newline normalization failed ($label): $root"
    }

    Write-Host "Preflighting eMule Next activators ($label)..."
    python (Join-Path $tools "audit-activators.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Activator preflight failed in clean activation overlay ($label): $root"
    }

    Write-Host "Activating eMule Next runtime features ($label)..."
    python (Join-Path $tools "activate-features.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Feature activation failed in clean activation overlay ($label): $root"
    }
}

function Get-ActivationTreeHash([string]$Root) {
    $rootPath = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\')
    $manifest = New-Object System.Collections.Generic.List[string]

    Get-ChildItem -LiteralPath $rootPath -Recurse -File | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($rootPath.Length).TrimStart('\').Replace('\', '/')
        $fileHash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $manifest.Add("$fileHash  $relative")
    }

    $payload = [System.Text.Encoding]::UTF8.GetBytes(($manifest -join "`n"))
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $digest = $sha.ComputeHash($payload)
    }
    finally {
        $sha.Dispose()
    }
    return ([System.BitConverter]::ToString($digest)).Replace('-', '').ToLowerInvariant()
}

# Activators are generation steps. We do NOT require a generated tree to be a
# valid input for the same legacy generation chain a second time. Instead we
# prove the property the build actually needs: two independent clean runs from
# the exact same repository input must produce byte-identical activated source.
$StageA = New-CleanActivationStage $StageRoot "A"
Invoke-CleanActivation $StageA
$HashA = Get-ActivationTreeHash $StageA.Source
Write-Host "Activation tree A: $HashA"

$StageB = New-CleanActivationStage $VerifyStageRoot "B"
Invoke-CleanActivation $StageB
$HashB = Get-ActivationTreeHash $StageB.Source
Write-Host "Activation tree B: $HashB"

if ($HashA -ne $HashB) {
    throw "Clean activation is not deterministic. Stage A kept at $StageRoot; stage B kept at $VerifyStageRoot"
}

Write-Host "Clean activation determinism verified: both independent stages are byte-identical."
Remove-StageIfPresent $VerifyStageRoot

$StageSource = $StageA.Source

if ($ActivationOnly) {
    Write-Host ""
    Write-Host "ACTIVATION SUCCESS"
    Write-Host "Integration, feature activation, all verifiers and clean-run determinism succeeded."
    Write-Host "Stage: $StageRoot"
    Write-Host "Repository overlay was not modified by integration/activation."
    if (-not $KeepActivationStage) {
        Remove-StageIfPresent $StageRoot
    }
    return
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

# Apply only the fully activated, independently reproducible staging overlay.
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

if (-not $KeepActivationStage) {
    Remove-StageIfPresent $StageRoot
}

Write-Host ""
Write-Host "SUCCESS"
Write-Host "Preview: $PreviewExe"
Write-Host "Latest alias: $LatestExe"
Write-Host "Repository overlay was not modified by integration/activation."
