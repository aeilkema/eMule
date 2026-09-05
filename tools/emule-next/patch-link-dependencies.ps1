[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ProjectPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
$text = [IO.File]::ReadAllText($ProjectPath)
$pattern = '<AdditionalDependencies>(.*?)</AdditionalDependencies>'
$regex = [Text.RegularExpressions.Regex]::new($pattern, [Text.RegularExpressions.RegexOptions]::Singleline)
$changed = $false

$updated = $regex.Replace($text, [Text.RegularExpressions.MatchEvaluator]{
    param($match)

    $value = $match.Groups[1].Value
    $deps = [Collections.Generic.List[string]]::new()
    foreach ($dep in ($value -split ';')) {
        if (-not [string]::IsNullOrWhiteSpace($dep)) {
            $deps.Add($dep)
        }
    }

    if (-not ($deps | Where-Object { $_ -ieq 'bcrypt.lib' })) {
        $deps.Insert(0, 'bcrypt.lib')
        $script:changed = $true
    }

    $mbedTlsEntries = @($deps | Where-Object { $_ -match '(?i)mbedtls\.lib$' })
    foreach ($entry in $mbedTlsEntries) {
        $prefix = $entry.Substring(0, $entry.Length - 'mbedtls.lib'.Length)
        foreach ($name in @('mbedx509.lib', 'tfpsacrypto.lib')) {
            $candidate = "$prefix$name"
            if (-not ($deps | Where-Object { $_ -ieq $candidate })) {
                $index = $deps.IndexOf($entry)
                $deps.Insert($index + 1, $candidate)
                $script:changed = $true
            }
        }
    }

    return '<AdditionalDependencies>' + (($deps -join ';') + ';') + '</AdditionalDependencies>'
})

if (-not $regex.IsMatch($text)) {
    throw "No AdditionalDependencies entries found in $ProjectPath"
}

if ($changed) {
    $utf8Bom = [Text.UTF8Encoding]::new($true)
    [IO.File]::WriteAllText($ProjectPath, $updated, $utf8Bom)
    Write-Host "Patched linker dependencies in $ProjectPath"
}
else {
    Write-Host "Linker dependencies already patched in $ProjectPath"
}

$check = [IO.File]::ReadAllText($ProjectPath)
foreach ($required in @('bcrypt.lib', 'mbedx509.lib', 'tfpsacrypto.lib')) {
    if ($check -notmatch [Regex]::Escape($required)) {
        throw "Required linker dependency was not written: $required"
    }
}
