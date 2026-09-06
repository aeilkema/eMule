[CmdletBinding()]
param(
    [switch]$DesktopShortcut,
    [string]$WixExe = "wix"
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$Artifacts = Join-Path $RepoRoot "artifacts"
$PreviewExe = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-x64.exe"
$SourceWxs = Join-Path $RepoRoot "installer\preview2\Product.wxs"
$GeneratedWxs = Join-Path $Artifacts "Product.Preview2.generated.wxs"
$OutputMsi = Join-Path $Artifacts "eMule-Next-0.2.0-Preview2-x64.msi"

if (-not (Test-Path -LiteralPath $PreviewExe -PathType Leaf)) {
    throw "Preview 2 executable not found: $PreviewExe. Run .\build-local.ps1 first."
}
if (-not (Test-Path -LiteralPath $SourceWxs -PathType Leaf)) {
    throw "WiX source not found: $SourceWxs"
}

$desktopComponent = @"
    <DirectoryRef Id="DesktopFolder">
      <Component Id="DesktopShortcut" Guid="*" Bitness="always64">
        <Shortcut Id="DesktopShortcutLink"
                  Name="eMule Next Preview 2"
                  Description="eMule Next Preview 2"
                  Target="[INSTALLFOLDER]eMule-Next.exe"
                  WorkingDirectory="INSTALLFOLDER" />
        <RegistryValue Root="HKLM"
                       Key="Software\eMule Next\Preview2"
                       Name="DesktopShortcut"
                       Type="integer"
                       Value="1"
                       KeyPath="yes" />
      </Component>
    </DirectoryRef>
"@
$desktopFeature = '      <ComponentRef Id="DesktopShortcut" />'

$wxs = Get-Content -LiteralPath $SourceWxs -Raw
if ($DesktopShortcut) {
    $wxs = $wxs.Replace('    <!--PREVIEW2_DESKTOP_COMPONENT-->', $desktopComponent)
    $wxs = $wxs.Replace('      <!--PREVIEW2_DESKTOP_FEATURE-->', $desktopFeature)
}
else {
    $wxs = $wxs.Replace('    <!--PREVIEW2_DESKTOP_COMPONENT-->', '')
    $wxs = $wxs.Replace('      <!--PREVIEW2_DESKTOP_FEATURE-->', '')
}
Set-Content -LiteralPath $GeneratedWxs -Value $wxs -Encoding utf8

$wixCommand = Get-Command $WixExe -ErrorAction SilentlyContinue
if ($null -eq $wixCommand) {
    throw "WiX CLI not found ('$WixExe'). Install a current WiX Toolset CLI and rerun this script."
}

& $WixExe build `
    -arch x64 `
    -d "PreviewExe=$PreviewExe" `
    -o $OutputMsi `
    $GeneratedWxs

if ($LASTEXITCODE -ne 0) {
    throw "WiX MSI build failed. Generated source kept at $GeneratedWxs"
}

Write-Host "MSI SUCCESS"
Write-Host "Installer: $OutputMsi"
if ($DesktopShortcut) {
    Write-Host "Desktop shortcut included."
}
else {
    Write-Host "Desktop shortcut omitted; Start Menu shortcut is included."
}
Get-FileHash -LiteralPath $OutputMsi -Algorithm SHA256
