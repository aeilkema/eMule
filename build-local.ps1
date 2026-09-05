[CmdletBinding()]
param(
    [ValidateSet('Release', 'Debug')][string]$Configuration = 'Release',
    [ValidateSet('x64')][string]$Platform = 'x64',
    [string]$PlatformToolset = 'v145'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

function Find-MSBuildWithMfc {
    $candidates = @(
        'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\MSBuild\Current\Bin\MSBuild.exe',
        'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe'
    )

    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        $vsRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $candidate)))
        $mfc = @(Get-ChildItem -LiteralPath (Join-Path $vsRoot 'VC\Tools\MSVC') -Recurse -Filter 'mfc140u.lib' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '[\\/]atlmfc[\\/]lib[\\/]x64[\\/]mfc140u\.lib$' } |
            Select-Object -First 1)
        if ($mfc.Count -gt 0) {
            return $candidate
        }
    }

    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path -LiteralPath $vswhere) {
        $found = @(& $vswhere -all -products * -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\MSBuild.exe')
        foreach ($candidate in $found) {
            if (-not [string]::IsNullOrWhiteSpace($candidate)) { return $candidate.Trim() }
        }
    }

    throw 'No suitable MSBuild installation was found. Visual Studio/Build Tools with Desktop C++ and x64 MFC is required.'
}

Write-Host '=== eMule Next local build ==='
Write-Host "Repository: $RepoRoot"

Write-Host 'Applying eMule Next integration...'
& python (Join-Path $RepoRoot 'tools\emule-next\integrate.py')
if ($LASTEXITCODE -ne 0) { throw 'eMule Next integration failed' }

Write-Host 'Bootstrapping official source and pinned dependencies...'
$lines = & (Join-Path $RepoRoot 'tools\emule-next\bootstrap-source.ps1') -SkipIntegration
if ($LASTEXITCODE -ne 0) { throw 'Source bootstrap failed' }
$sourceDir = ($lines | Select-Object -Last 1).Trim()
if (-not (Test-Path -LiteralPath (Join-Path $sourceDir 'emule.vcxproj'))) {
    throw "emule.vcxproj not found in $sourceDir"
}
Write-Host "Source: $sourceDir"

$msbuild = Find-MSBuildWithMfc
Write-Host "MSBuild: $msbuild"

Write-Host 'Provisioning pinned WinSQLite import library...'
$sdkPackageVersion = '10.0.26100.7705'
$packageId = 'microsoft.windows.sdk.cpp.x64'
$packageRoot = Join-Path $RepoRoot 'build\winsqlite-sdk'
$archive = Join-Path $packageRoot "$packageId.nupkg"
$extract = Join-Path $packageRoot $packageId
New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
if (-not (Test-Path -LiteralPath $archive)) {
    $url = "https://api.nuget.org/v3-flatcontainer/$packageId/$sdkPackageVersion/$packageId.$sdkPackageVersion.nupkg"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $archive
}
if (Test-Path -LiteralPath $extract) { Remove-Item -LiteralPath $extract -Recurse -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::ExtractToDirectory($archive, $extract)
$winSqlite = Get-ChildItem -LiteralPath $extract -Recurse -Filter 'winsqlite3.lib' -File |
    Where-Object { $_.FullName -match '[\\/]x64[\\/]' } |
    Select-Object -First 1
if ($null -eq $winSqlite) { throw 'Pinned Windows SDK package did not contain winsqlite3.lib' }
$env:LIB = if ([string]::IsNullOrWhiteSpace($env:LIB)) { $winSqlite.Directory.FullName } else { "$($winSqlite.Directory.FullName);$env:LIB" }

Write-Host 'Building dependencies...'
& (Join-Path $RepoRoot 'tools\emule-next\build-dependencies.ps1') `
    -SourceDir $sourceDir `
    -MSBuildExe $msbuild `
    -Configuration $Configuration `
    -Platform $Platform `
    -PlatformToolset $PlatformToolset
if ($LASTEXITCODE -ne 0) { throw 'Dependency build failed' }

$project = Join-Path $sourceDir 'emule.vcxproj'
& (Join-Path $RepoRoot 'tools\emule-next\patch-link-dependencies.ps1') -ProjectPath $project

$installedSdk = Get-ChildItem -LiteralPath "${env:ProgramFiles(x86)}\Windows Kits\10\Include" -Directory |
    Sort-Object { try { [Version]$_.Name } catch { [Version]'0.0' } } -Descending |
    Select-Object -First 1
if ($null -eq $installedSdk) { throw 'No installed Windows SDK was found' }

Write-Host "Building eMule Next $Configuration $Platform..."
& $msbuild $project `
    /m `
    /t:Build `
    /p:BuildProjectReferences=false `
    "/p:Configuration=$Configuration" `
    "/p:Platform=$Platform" `
    "/p:PlatformToolset=$PlatformToolset" `
    "/p:WindowsTargetPlatformVersion=$($installedSdk.Name)" `
    /verbosity:minimal
if ($LASTEXITCODE -ne 0) { throw 'eMule build failed' }

$exe = Join-Path $sourceDir "$Platform\$Configuration\emule.exe"
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "Build succeeded but executable was not found: $exe"
}

$releaseDir = Join-Path $RepoRoot 'artifacts\release'
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
$output = Join-Path $releaseDir 'eMule-Next-x64.exe'
Copy-Item -LiteralPath $exe -Destination $output -Force
$hash = Get-FileHash -LiteralPath $output -Algorithm SHA256
$hash | Format-List | Out-File (Join-Path $releaseDir 'SHA256.txt')

Write-Host ''
Write-Host '=== BUILD SUCCEEDED ==='
Write-Host "Executable: $output"
Write-Host "SHA256: $($hash.Hash)"
