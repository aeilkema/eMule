[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$DiagnosticsReport,
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$Artifacts = Join-Path $RepoRoot "artifacts"
$Exe = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-x64.exe"

if (-not (Test-Path -LiteralPath $DiagnosticsReport -PathType Leaf)) {
    throw "Diagnostics report not found: $DiagnosticsReport"
}
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = $Artifacts
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$stamp = [DateTime]::Now.ToString('yyyyMMdd-HHmmss')
$stage = Join-Path $Artifacts "preview2-support-$stamp"
$zip = Join-Path $OutputDirectory "eMule-Next-Preview2-support-$stamp.zip"
New-Item -ItemType Directory -Force -Path $stage | Out-Null

try {
    Copy-Item -LiteralPath $DiagnosticsReport -Destination (Join-Path $stage "diagnostics.txt") -Force

    foreach ($pair in @(
        @{ Source = "docs\EMULE_NEXT_PREVIEW2_RELEASE_NOTES.md"; Destination = "RELEASE-NOTES.md" },
        @{ Source = "docs\EMULE_NEXT_RUNTIME_TEST_MATRIX.md"; Destination = "RUNTIME-TEST-MATRIX.md" }
    )) {
        $source = Join-Path $RepoRoot $pair.Source
        if (Test-Path -LiteralPath $source -PathType Leaf) {
            Copy-Item -LiteralPath $source -Destination (Join-Path $stage $pair.Destination) -Force
        }
    }

    $head = (& git -C $RepoRoot rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0) { $head = "unknown" }
    $exeHash = "not built"
    if (Test-Path -LiteralPath $Exe -PathType Leaf) {
        $exeHash = (Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash.ToLowerInvariant()
    }

    $system = @(
        "eMule Next Preview 2 support bundle",
        "Generated: $([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss zzz'))",
        "Git head: $($head.ToString().Trim())",
        "Executable SHA256: $exeHash",
        "Windows: $([Environment]::OSVersion.VersionString)",
        "64-bit OS: $([Environment]::Is64BitOperatingSystem)",
        "64-bit process: $([Environment]::Is64BitProcess)",
        "",
        "Privacy contract:",
        "- no intelligence SQLite database",
        "- no preferences/config files",
        "- no peer history or known.met",
        "- no incomplete download .part/.part.met files",
        "- no arbitrary log folders"
    )
    Set-Content -LiteralPath (Join-Path $stage "SYSTEM.txt") -Value $system -Encoding utf8

    if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip -CompressionLevel Optimal
    Write-Host "SUPPORT BUNDLE SUCCESS"
    Write-Host "Bundle: $zip"
    Get-FileHash -LiteralPath $zip -Algorithm SHA256
}
finally {
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
