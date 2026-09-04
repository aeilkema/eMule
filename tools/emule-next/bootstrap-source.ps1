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

# The official eMule source package intentionally does not contain the sibling
# third-party projects referenced by emule.sln/emule.vcxproj.  Pin every build
# dependency to an exact commit so CI and local builds do not drift when a
# dependency branch advances.
$Dependencies = @(
    [pscustomobject]@{
        Name = 'cryptopp'
        Url = 'https://github.com/emulebb/emulebb-cryptopp.git'
        Commit = '5279c7a811a97b574a839ea89b4c30ad337e6675'
        SourceSubdir = '.'
        Destination = 'cryptopp'
        Project = 'cryptlib.vcxproj'
        RecurseSubmodules = $false
    },
    [pscustomobject]@{
        Name = 'id3lib'
        Url = 'https://github.com/emulebb/emulebb-id3lib.git'
        Commit = 'fc66770df4ec3309fb4acb2ea570bf940f5c96eb'
        SourceSubdir = '.'
        Destination = 'id3lib'
        Project = 'libprj\id3lib.vcxproj'
        RecurseSubmodules = $false
    },
    [pscustomobject]@{
        Name = 'mbedtls'
        Url = 'https://github.com/emulebb/emulebb-mbedtls.git'
        Commit = '4f8ce00444e273babc61d647639e180e5aed56f2'
        SourceSubdir = '.'
        Destination = 'mbedtls'
        Project = 'visualc\VS2017\mbedTLS.vcxproj'
        RecurseSubmodules = $true
    },
    [pscustomobject]@{
        Name = 'miniupnpc'
        Url = 'https://github.com/emulebb/emulebb-miniupnp.git'
        Commit = '036997224e4318de31a8bbf9ae52d03b0726691e'
        SourceSubdir = 'miniupnpc'
        Destination = 'miniupnpc'
        Project = 'msvc\miniupnpc.vcxproj'
        RecurseSubmodules = $false
    },
    [pscustomobject]@{
        Name = 'ResizableLib'
        Url = 'https://github.com/emulebb/emulebb-resizablelib.git'
        Commit = 'a7b01a31296b7fe2ed3331171e126ebd9cb1652a'
        SourceSubdir = 'ResizableLib'
        Destination = 'ResizableLib'
        Project = 'ResizableLib.vcxproj'
        RecurseSubmodules = $false
    },
    [pscustomobject]@{
        Name = 'zlib'
        Url = 'https://github.com/emulebb/emulebb-zlib.git'
        Commit = '31fd978c8b2cf375b3935a8279bc599cc07e2a6a'
        SourceSubdir = '.'
        Destination = 'zlib'
        Project = 'contrib\vstudio\vc\zlib.vcxproj'
        RecurseSubmodules = $false
    }
)

New-Item -ItemType Directory -Force -Path $CacheDir | Out-Null

function Test-ArchiveHash {
    if (-not (Test-Path -LiteralPath $Archive)) { return $false }
    $actual = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
    return $actual -eq $ExpectedSha256
}

function Invoke-GitChecked {
    param(
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & git -C $WorkingDirectory @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git failed in $WorkingDirectory: git $($Arguments -join ' ')"
    }
}

function Materialize-Dependency {
    param(
        [Parameter(Mandatory = $true)]$Spec,
        [Parameter(Mandatory = $true)][string]$CloneRoot,
        [Parameter(Mandatory = $true)][string]$TargetRoot
    )

    $clone = Join-Path $CloneRoot $Spec.Name
    if (Test-Path -LiteralPath $clone) {
        Remove-Item -LiteralPath $clone -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $clone | Out-Null

    Write-Host "Materializing $($Spec.Name) at $($Spec.Commit)..."
    Invoke-GitChecked -WorkingDirectory $clone -Arguments @('init', '--quiet')
    Invoke-GitChecked -WorkingDirectory $clone -Arguments @('remote', 'add', 'origin', $Spec.Url)
    Invoke-GitChecked -WorkingDirectory $clone -Arguments @('fetch', '--quiet', '--depth', '1', 'origin', $Spec.Commit)
    Invoke-GitChecked -WorkingDirectory $clone -Arguments @('checkout', '--quiet', '--detach', 'FETCH_HEAD')
    if ($Spec.RecurseSubmodules) {
        Invoke-GitChecked -WorkingDirectory $clone -Arguments @('submodule', 'update', '--init', '--recursive', '--depth', '1')
    }

    $actualCommit = (& git -C $clone rev-parse HEAD).Trim()
    if ($actualCommit -ne $Spec.Commit) {
        throw "Dependency $($Spec.Name) resolved to $actualCommit instead of pinned $($Spec.Commit)"
    }

    $source = if ($Spec.SourceSubdir -eq '.') { $clone } else { Join-Path $clone $Spec.SourceSubdir }
    if (-not (Test-Path -LiteralPath $source -PathType Container)) {
        throw "Dependency $($Spec.Name) is missing source subdirectory $($Spec.SourceSubdir)"
    }

    $target = Join-Path $TargetRoot $Spec.Destination
    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Get-ChildItem -LiteralPath $source -Force |
        Where-Object { $_.Name -ne '.git' } |
        ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $target -Recurse -Force }

    $project = Join-Path $target $Spec.Project
    if (-not (Test-Path -LiteralPath $project -PathType Leaf)) {
        throw "Dependency $($Spec.Name) did not provide expected project $project"
    }
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

# Restore the sibling dependency projects which the upstream solution expects.
$CloneRoot = Join-Path $Destination '_dependency-clones'
New-Item -ItemType Directory -Force -Path $CloneRoot | Out-Null
foreach ($dependency in $Dependencies) {
    Materialize-Dependency -Spec $dependency -CloneRoot $CloneRoot -TargetRoot $TargetRoot
}
Remove-Item -LiteralPath $CloneRoot -Recurse -Force

# v0.72a carries a small eMule-specific Mbed TLS overlay (currently the custom
# threading header). Apply it only after the complete pinned Mbed TLS tree is in
# place so the overlay cannot be lost when dependencies are materialized.
$OverlayMbed = Join-Path $RepoRoot 'mbedtls'
$TargetMbed = Join-Path $TargetRoot 'mbedtls'
if (Test-Path -LiteralPath $OverlayMbed) {
    Get-ChildItem -LiteralPath $OverlayMbed -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $TargetMbed -Recurse -Force
    }
}

# Verify the packaging gaps which motivated the bootstrap are now resolved.
$RequiredSource = @(
    'UpDownClient.h',
    'emule.vcxproj',
    'ClientList.cpp',
    'DownloadQueue.cpp'
)
foreach ($name in $RequiredSource) {
    $candidate = Join-Path $TargetSource $name
    if (-not (Test-Path -LiteralPath $candidate)) {
        # Some official source packages use lowercase legacy filenames.
        $lower = Join-Path $TargetSource $name.ToLowerInvariant()
        if (-not (Test-Path -LiteralPath $lower)) {
            throw "Bootstrapped tree is incomplete: missing $name"
        }
    }
}

foreach ($dependency in $Dependencies) {
    $project = Join-Path (Join-Path $TargetRoot $dependency.Destination) $dependency.Project
    if (-not (Test-Path -LiteralPath $project -PathType Leaf)) {
        throw "Bootstrapped tree is incomplete: missing dependency project $project"
    }
}

$ManifestDependencies = @(
    foreach ($dependency in $Dependencies) {
        [ordered]@{
            name = $dependency.Name
            url = $dependency.Url
            commit = $dependency.Commit
            destination = $dependency.Destination
            project = $dependency.Project
        }
    }
)
$Manifest = [ordered]@{
    source_url = $SourceUrl
    source_sha256 = $ExpectedSha256
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    repository_commit = (& git -C $RepoRoot rev-parse HEAD 2>$null)
    source_directory = $TargetSource
    dependencies = $ManifestDependencies
}
$Manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $Destination 'emule-next-bootstrap.json') -Encoding UTF8

Write-Host "eMule Next full source tree ready at: $TargetSource"
Write-Output $TargetSource
