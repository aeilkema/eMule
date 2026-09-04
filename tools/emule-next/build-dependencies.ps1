[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SourceDir,
    [Parameter(Mandatory = $true)][string]$MSBuildExe,
    [ValidateSet('Debug', 'Release')][string]$Configuration = 'Release',
    [ValidateSet('x64', 'ARM64')][string]$Platform = 'x64',
    [string]$PlatformToolset = 'v143'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$SourceDir = (Resolve-Path -LiteralPath $SourceDir).Path
$MSBuildExe = (Resolve-Path -LiteralPath $MSBuildExe).Path
$Root = Split-Path -Parent $SourceDir

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [string]$WorkingDirectory = $Root
    )

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$FilePath failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-MSBuildProject {
    param([Parameter(Mandatory = $true)][string]$Project)

    if (-not (Test-Path -LiteralPath $Project -PathType Leaf)) {
        throw "Dependency project not found: $Project"
    }
    Write-Host "Building dependency project: $Project"
    $arguments = @(
        $Project,
        '/m',
        '/t:Build',
        "/p:Configuration=$Configuration",
        "/p:Platform=$Platform",
        "/p:PlatformToolset=$PlatformToolset",
        "/p:DefaultPlatformToolset=$PlatformToolset",
        '/p:WindowsTargetPlatformVersion=10.0',
        '/verbosity:minimal'
    )
    Invoke-Checked -FilePath $MSBuildExe -Arguments $arguments -WorkingDirectory (Split-Path -Parent $Project)
}

function Resolve-CMakeGenerator {
    # VS 2026 installs under an 18.x path; VS 2022 commonly uses either a 17.x
    # path or a year-based path. Keep the decision local to the selected MSBuild.
    if ($MSBuildExe -match '[\\/]18[\\/]') { return 'Visual Studio 18 2026' }
    if ($MSBuildExe -match '[\\/]2026[\\/]') { return 'Visual Studio 18 2026' }
    return 'Visual Studio 17 2022'
}

function Resolve-Perl {
    $perl = Get-Command perl.exe -ErrorAction SilentlyContinue
    if ($null -ne $perl) { return $perl.Source }

    $candidates = @(
        'C:\Program Files\Git\usr\bin\perl.exe',
        'C:\Program Files (x86)\Git\usr\bin\perl.exe'
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw 'Perl is required to generate Mbed TLS sources but perl.exe was not found'
}

function Resolve-Python {
    foreach ($name in @('python.exe', 'python3.exe', 'py.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -eq $command) { continue }
        if ($name -eq 'py.exe') {
            # py.exe is a launcher, not the interpreter path CMake expects.
            $path = & $command.Source -3 -c 'import sys; print(sys.executable)'
            if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($path)) {
                return $path.Trim()
            }
            continue
        }
        return $command.Source
    }
    throw 'Python 3 is required to generate Mbed TLS sources but no interpreter was found'
}

function Ensure-MbedTlsPythonPackages {
    param([Parameter(Mandatory = $true)][string]$PythonExe)

    # The pinned TF-PSA generator imports exactly jsonschema and jinja2. Install
    # modern, deterministic versions instead of the historical full requirements
    # file, which pins an obsolete MarkupSafe release incompatible with new Python.
    $probe = @'
import jsonschema
import jinja2
assert jsonschema.__version__
assert jinja2.__version__
'@
    & $PythonExe -c $probe 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host 'Mbed TLS Python generator packages already available.'
        return
    }

    Write-Host 'Installing pinned Mbed TLS Python generator packages...'
    Invoke-Checked -FilePath $PythonExe -Arguments @(
        '-m', 'pip', 'install',
        '--disable-pip-version-check',
        '--no-input',
        'Jinja2==3.1.6',
        'jsonschema==4.25.1'
    )

    Invoke-Checked -FilePath $PythonExe -Arguments @(
        '-c', 'import jsonschema, jinja2; print("Mbed TLS Python generator packages OK")'
    )
}

function Ensure-Id3ZlibCompatibility {
    # The maintained id3lib project still names its sibling include folder
    # "emulebb-zlib", while eMule's own project expects the sibling as "zlib".
    # A directory junction keeps one pinned zlib tree and satisfies both build
    # layouts without copying or modifying third-party source files.
    $zlib = Join-Path $Root 'zlib'
    $alias = Join-Path $Root 'emulebb-zlib'
    if (-not (Test-Path -LiteralPath $zlib -PathType Container)) {
        throw "Pinned zlib source directory not found: $zlib"
    }
    if (Test-Path -LiteralPath $alias) {
        return
    }

    New-Item -ItemType Junction -Path $alias -Target $zlib | Out-Null
    if (-not (Test-Path -LiteralPath (Join-Path $alias 'zlib.h') -PathType Leaf)) {
        throw 'id3lib zlib compatibility junction was created but zlib.h is not visible'
    }
    Write-Host "Created id3lib zlib include alias: $alias -> $zlib"
}

function Find-Library {
    param(
        [Parameter(Mandatory = $true)][string]$SearchRoot,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $matches = @(Get-ChildItem -LiteralPath $SearchRoot -Recurse -File -Filter $Name -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending)
    if ($matches.Count -eq 0) {
        throw "Built library $Name was not found below $SearchRoot"
    }
    return $matches[0].FullName
}

function Stage-Library {
    param(
        [Parameter(Mandatory = $true)][string]$SearchRoot,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $source = Find-Library -SearchRoot $SearchRoot -Name $Name
    $destinationDir = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
    if ([IO.Path]::GetFullPath($source) -ne [IO.Path]::GetFullPath($Destination)) {
        Copy-Item -LiteralPath $source -Destination $Destination -Force
    }
    Write-Host "Staged $Name -> $Destination"
}

function Build-MbedTls {
    $source = Join-Path $Root 'mbedtls'
    $build = Join-Path $source "cmake-emule-next-$Platform"
    $generator = Resolve-CMakeGenerator
    $perl = Resolve-Perl
    $python = Resolve-Python
    $runtime = if ($Configuration -eq 'Debug') { 'MultiThreadedDebug' } else { 'MultiThreaded' }

    Ensure-MbedTlsPythonPackages -PythonExe $python

    if (Test-Path -LiteralPath $build) {
        Remove-Item -LiteralPath $build -Recurse -Force
    }

    Write-Host "Configuring Mbed TLS using $generator..."
    Invoke-Checked -FilePath 'cmake.exe' -WorkingDirectory $source -Arguments @(
        '-S', $source,
        '-B', $build,
        '-G', $generator,
        '-A', $Platform,
        '-T', $PlatformToolset,
        '-DENABLE_PROGRAMS=OFF',
        '-DENABLE_TESTING=OFF',
        '-DGEN_FILES=ON',
        '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
        '-DCMAKE_POLICY_DEFAULT_CMP0091=NEW',
        "-DCMAKE_MSVC_RUNTIME_LIBRARY=$runtime",
        "-DPERL_EXECUTABLE=$perl",
        "-DPython3_EXECUTABLE=$python"
    )
    Invoke-Checked -FilePath 'cmake.exe' -WorkingDirectory $source -Arguments @(
        '--build', $build,
        '--config', $Configuration,
        '--parallel'
    )

    $stage = Join-Path $source "visualc\VS2017\$Platform\$Configuration"
    Stage-Library -SearchRoot $build -Name 'mbedtls.lib' -Destination (Join-Path $stage 'mbedtls.lib')
    Stage-Library -SearchRoot $build -Name 'mbedx509.lib' -Destination (Join-Path $stage 'mbedx509.lib')
    Stage-Library -SearchRoot $build -Name 'tfpsacrypto.lib' -Destination (Join-Path $stage 'tfpsacrypto.lib')

    # Some future Mbed TLS layouts may split an additional mbedcrypto library.
    # Stage it when present; the current pinned 4.1 eMule fork does not require it.
    $crypto = @(Get-ChildItem -LiteralPath $build -Recurse -File -Filter 'mbedcrypto.lib' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1)
    if ($crypto.Count -gt 0) {
        Copy-Item -LiteralPath $crypto[0].FullName -Destination (Join-Path $stage 'mbedcrypto.lib') -Force
    }
}

function Build-Zlib {
    $source = Join-Path $Root 'zlib'
    $build = Join-Path $source "cmake-emule-next-$Platform"
    $generator = Resolve-CMakeGenerator
    $runtime = if ($Configuration -eq 'Debug') { 'MultiThreadedDebug' } else { 'MultiThreaded' }

    if (Test-Path -LiteralPath $build) {
        Remove-Item -LiteralPath $build -Recurse -Force
    }

    Write-Host "Configuring zlib using $generator..."
    Invoke-Checked -FilePath 'cmake.exe' -WorkingDirectory $source -Arguments @(
        '-S', $source,
        '-B', $build,
        '-G', $generator,
        '-A', $Platform,
        '-T', $PlatformToolset,
        '-DZLIB_BUILD_SHARED=OFF',
        '-DZLIB_BUILD_TESTING=OFF',
        "-DCMAKE_MSVC_RUNTIME_LIBRARY=$runtime"
    )
    Invoke-Checked -FilePath 'cmake.exe' -WorkingDirectory $source -Arguments @(
        '--build', $build,
        '--config', $Configuration,
        '--target', 'zlibstatic',
        '--parallel'
    )

    $stage = Join-Path $source "contrib\vstudio\vc\$Platform\$Configuration\zlib.lib"
    $candidates = @('zlibstatic.lib', 'zs.lib', 'zsd.lib', 'zlib.lib')
    $found = $null
    foreach ($name in $candidates) {
        $match = @(Get-ChildItem -LiteralPath $build -Recurse -File -Filter $name -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1)
        if ($match.Count -gt 0) {
            $found = $match[0].FullName
            break
        }
    }
    if ($null -eq $found) {
        throw "Built zlib static library was not found below $build"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $stage) | Out-Null
    Copy-Item -LiteralPath $found -Destination $stage -Force
    Write-Host "Staged zlib -> $stage"
}

# Build the projects which already have modern eMule-compatible VS wrappers.
Ensure-Id3ZlibCompatibility
Invoke-MSBuildProject -Project (Join-Path $Root 'cryptopp\cryptlib.vcxproj')
Invoke-MSBuildProject -Project (Join-Path $Root 'id3lib\libprj\id3lib.vcxproj')
Invoke-MSBuildProject -Project (Join-Path $Root 'miniupnpc\msvc\miniupnpc.vcxproj')
Invoke-MSBuildProject -Project (Join-Path $Root 'ResizableLib\ResizableLib.vcxproj')

# Mbed TLS and zlib wrappers in the dependency forks intentionally delegate to
# CMake. Building them directly here lets us select the installed VS generator
# (including VS 2026) instead of depending on an old hard-coded generator name.
Build-MbedTls
Build-Zlib

# Normalize output locations to the paths hard-coded by the legacy eMule project.
Stage-Library -SearchRoot (Join-Path $Root 'cryptopp') -Name 'cryptlib.lib' -Destination (Join-Path $Root "cryptopp\$Platform\$Configuration\cryptlib.lib")
Stage-Library -SearchRoot (Join-Path $Root 'id3lib') -Name 'id3lib.lib' -Destination (Join-Path $Root "id3lib\libprj\$Platform\$Configuration\id3lib.lib")
Stage-Library -SearchRoot (Join-Path $Root 'miniupnpc') -Name 'miniupnpc.lib' -Destination (Join-Path $Root "miniupnpc\msvc\$Platform\$Configuration\miniupnpc.lib")
Stage-Library -SearchRoot (Join-Path $Root 'ResizableLib') -Name 'ResizableLib.lib' -Destination (Join-Path $Root "ResizableLib\$Platform\$Configuration\ResizableLib.lib")

$RequiredLibraries = @(
    (Join-Path $Root "cryptopp\$Platform\$Configuration\cryptlib.lib"),
    (Join-Path $Root "id3lib\libprj\$Platform\$Configuration\id3lib.lib"),
    (Join-Path $Root "mbedtls\visualc\VS2017\$Platform\$Configuration\mbedtls.lib"),
    (Join-Path $Root "mbedtls\visualc\VS2017\$Platform\$Configuration\mbedx509.lib"),
    (Join-Path $Root "mbedtls\visualc\VS2017\$Platform\$Configuration\tfpsacrypto.lib"),
    (Join-Path $Root "miniupnpc\msvc\$Platform\$Configuration\miniupnpc.lib"),
    (Join-Path $Root "ResizableLib\$Platform\$Configuration\ResizableLib.lib"),
    (Join-Path $Root "zlib\contrib\vstudio\vc\$Platform\$Configuration\zlib.lib")
)
foreach ($library in $RequiredLibraries) {
    if (-not (Test-Path -LiteralPath $library -PathType Leaf)) {
        throw "Dependency staging failed: missing $library"
    }
}

Write-Host "All eMule dependencies are built and staged for $Platform|$Configuration."
