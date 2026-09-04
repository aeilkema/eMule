[CmdletBinding()]
param(
    [string]$Destination = "",
    [switch]$SkipIntegration
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($Destination)) {
    $Destination = Join-Path $RepoRoot 'build\upstream-v0.72a'
}
$Destination = [IO.Path]::GetFullPath($Destination)

$SourceUrl = 'https://github.com/irwir/eMule/releases/download/eMule_v0.72a-community/eMule0.72a-Sources.zip'
$ExpectedSha256 = '7457d2b9b11c7800b79f29579854492ab04888ec55c37d78494cf7900f100f9a'
$CacheDir = Join-Path $RepoRoot 'build\cache'
$Archive = Join-Path $CacheDir 'eMule0.72a-Sources.zip'

New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null

function Test-ArchiveHash {
    if (-not (Test-Path -LiteralPath $Archive)) { return $false }
    $actual = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
    return $actual -eq $ExpectedSha256
}

if (-not (Test-ArchiveHash)) {
    if (Test-Path -LiteralPath $Archive) {
        Remove-Item -LiteralPath $Archive -Force
    }
    Write-Host "Downloading official eMule v0.72a source release..."
    Invoke-WebRequest -UseBasicParsing -Uri $SourceUrl -OutFile $Archive
    if (-not (Test-ArchiveHash)) {
        $actual = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
        throw "Source archive hash mismatch. Expected $ExpectedSha256, got $actual"
    }
}

if (-not $SkipIntegration) {
    Write-Host 'Applying idempotent eMule Next integration to repository overlay...'
    & python (Join-Path $PSScriptRoot 'integrate.py')
    if ($LASTEXITCODE -ne 0) { throw 'integrate.py failed' }
}

if (Test-Path -LiteralPath $Destination) {
    Remove-Item -LiteralPath $Destination -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
Expand-Archive -LiteralPath $Archive -DestinationPath $Destination -Force

$Project = Get-ChildItem -LiteralPath $Destination -Recurse -Filter 'emule.vcxproj' -File |
    Select-Object -First 1
if ($null -eq $Project) {
    throw 'Official source archive did not contain emule.vcxproj'
}

$TargetSource = $Project.Directory.FullName
$TargetRoot = Split-Path -Parent $TargetSource
Write-Host "Full source directory: $TargetSource"

# The Git branch is an overlay. Copy it over the complete official source
# release without deleting files which exist only in the source package.
$OverlaySource = Join-Path $RepoRoot 'srchybrid'
Get-ChildItem -LiteralPath $OverlaySource -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination $TargetSource -Recurse -Force
}

$OverlayMbed = Join-Path $RepoRoot 'mbedtls'
$TargetMbed = Join-Path $TargetRoot 'mbedtls'
if ((Test-Path -LiteralPath $OverlayMbed) -and (Test-Path -LiteralPath $TargetMbed)) {
    Get-ChildItem -LiteralPath $OverlayMbed -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $TargetMbed -Recurse -Force
    }
}

# Verify the packaging gaps which motivated the bootstrap are now resolved.
$Required = @(
    'UpDownClient.h',
    'emule.vcxproj',
    'ClientList.cpp',
    'DownloadQueue.cpp'
)
foreach ($name in $Required) {
    $candidate = Join-Path $TargetSource $name
    if (-not (Test-Path -LiteralPath $candidate)) {
        # Some official source packages use lowercase legacy filenames.
        $lower = Join-Path $TargetSource $name.ToLowerInvariant()
        if (-not (Test-Path -LiteralPath $lower)) {
            throw "Bootstrapped tree is incomplete: missing $name"
        }
    }
}

$Manifest = [ordered]@{
    source_url = $SourceUrl
    source_sha256 = $ExpectedSha256
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    repository_commit = (& git -C $RepoRoot rev-parse HEAD 2>$null)
    source_directory = $TargetSource
}
$Manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Destination 'emule-next-bootstrap.json') -Encoding UTF8

Write-Host "eMule Next full source tree ready at: $TargetSource"
Write-Output $TargetSource
