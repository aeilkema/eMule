[CmdletBinding()]
param(
    [switch]$RebuildDependencies
)

$ErrorActionPreference = 'Stop'

$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

$MSBuild = "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\MSBuild.exe"
$PreviewExeName = "eMule-Next-0.1.0-Preview1-x64.exe"
$LatestExeName = "eMule-Next-x64.exe"

if (-not (Test-Path $MSBuild)) {
    throw "Visual Studio 2026 Build Tools MSBuild niet gevonden: $MSBuild"
}

Write-Host "Applying eMule Next integration..."
python .\tools\emule-next\integrate.py
if ($LASTEXITCODE -ne 0) {
    throw "Integration failed."
}

Write-Host "Activating eMule Next runtime features..."
python .\tools\emule-next\activate-features.py
if ($LASTEXITCODE -ne 0) {
    throw "Feature activation failed."
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

# Apply the current repository overlay to the generated source tree.
Get-ChildItem .\srchybrid -Force | ForEach-Object {
    Copy-Item $_.FullName -Destination $SourceDir -Recurse -Force
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
    throw "eMule build failed."
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

Write-Host ""
Write-Host "SUCCESS"
Write-Host "Preview: $PreviewExe"
Write-Host "Latest alias: $LatestExe"
