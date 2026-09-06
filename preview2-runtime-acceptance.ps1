[CmdletBinding(DefaultParameterSetName='Status')]
param(
    [Parameter(ParameterSetName='Init')][switch]$Initialize,
    [Parameter(ParameterSetName='Run')][switch]$Run,
    [Parameter(ParameterSetName='Status')][switch]$Status,
    [Parameter(ParameterSetName='Pass', Mandatory=$true)][string]$Pass,
    [Parameter(ParameterSetName='Fail', Mandatory=$true)][string]$Fail,
    [Parameter(ParameterSetName='VerifyCore')][switch]$VerifyCore,
    [Parameter(ParameterSetName='VerifyAll')][switch]$VerifyAll,
    [Parameter(ParameterSetName='Pass')][Parameter(ParameterSetName='Fail')][string]$Note = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$Artifacts = Join-Path $RepoRoot 'artifacts'
$Exe = Join-Path $Artifacts 'eMule-Next-0.2.0-Preview2-x64.exe'
$Record = Join-Path $Artifacts 'preview2-runtime-acceptance.json'
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$Checks = @(
    [pscustomobject]@{ id='UI-STARTUP'; group='core'; title='Startup shows the modern Preview 2 shell/sidebar/header' },
    [pscustomobject]@{ id='UI-NAV'; group='core'; title='All primary routes open correctly: Dashboard, Transfers, Search, Library, Shared Files, Known Users, Messages, Servers, Kad, Statistics, Settings, Diagnostics, IRC' },
    [pscustomobject]@{ id='UI-SEARCH-BRIDGE'; group='core'; title='Search opens Search 2 and Network search... opens authoritative legacy eD2K/Kad search' },
    [pscustomobject]@{ id='UI-SETTINGS'; group='core'; title='Settings shows 19 categories and original pages open the correct upstream Preferences page' },
    [pscustomobject]@{ id='UI-HEADER'; group='core'; title='Header connection state and transfer rates update correctly' },
    [pscustomobject]@{ id='UI-DASHBOARD'; group='core'; title='Dashboard primary actions, filters and More... actions work' },
    [pscustomobject]@{ id='THEME-DARK'; group='core'; title='Dark mode has no large white primary-workspace surfaces, including Messages/Chat' },
    [pscustomobject]@{ id='THEME-SWITCH'; group='core'; title='Dark -> Light -> System -> Dark applies without restart' },
    [pscustomobject]@{ id='DPI-MATRIX'; group='core'; title='UI is usable at 100%, 125%, 150% and 200% DPI and during resize' },
    [pscustomobject]@{ id='DIAG-STRESS'; group='core'; title='Diagnostics self-test PASS: ClientIndex 10000, DownloadIndex 5000, writer queue 10000' },
    [pscustomobject]@{ id='DIAG-DB'; group='core'; title='Database integrity, backup and WAL checkpoint actions complete successfully' },
    [pscustomobject]@{ id='ED2K'; group='core'; title='eD2K server connect, search, download, pause/resume and reconnect work' },
    [pscustomobject]@{ id='KAD'; group='core'; title='Kad bootstrap/connect, search, source lookup and restart work' },
    [pscustomobject]@{ id='UPLOAD'; group='core'; title='Upload/queue behavior and transfer history work' },
    [pscustomobject]@{ id='INTELLIGENCE'; group='core'; title='Source intelligence, Smart ETA, A4AF, rare parts and scheduler Analysis/Assist behave correctly' },
    [pscustomobject]@{ id='KNOWN-USERS'; group='core'; title='Known Users userhash identity, alias, favorite, history deletion and shared-files cooldown behavior work' },
    [pscustomobject]@{ id='LIBRARY'; group='core'; title='Library Download again, relink, missing and Available again flows work' },
    [pscustomobject]@{ id='PERSISTENCE'; group='core'; title='Restart preserves downloads, settings, library, aliases/favorites and database state' },
    [pscustomobject]@{ id='RECOVERY'; group='core'; title='Disposable database corruption/restore and abnormal-stop recovery behave safely' },
    [pscustomobject]@{ id='SUPPORT'; group='core'; title='Diagnostics report and support bundle can be created and contain no private user state' },
    [pscustomobject]@{ id='PORTABLE'; group='package'; title='Portable package clean-unpack/start works' },
    [pscustomobject]@{ id='MSI-INSTALL'; group='package'; title='MSI clean install and launch work' },
    [pscustomobject]@{ id='MSI-UPGRADE'; group='package'; title='Preview1/older install upgrade preserves configuration, DB and incomplete downloads' },
    [pscustomobject]@{ id='MSI-UNINSTALL'; group='package'; title='MSI uninstall removes program files without deleting user state' }
)

function Get-BuildIdentity {
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) {
        throw "Preview 2 executable missing: $Exe. Build the exact head first."
    }
    $head = (& git -C $RepoRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($head)) {
        throw 'Unable to resolve Git HEAD.'
    }
    $hash = (Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash.ToLowerInvariant()
    [pscustomobject]@{ head=$head; exeSha256=$hash }
}

function New-Record {
    $identity = Get-BuildIdentity
    $items = @()
    foreach ($check in $Checks) {
        $items += [pscustomobject]@{
            id = $check.id
            group = $check.group
            title = $check.title
            status = 'NOT_TESTED'
            note = ''
            updated = $null
        }
    }
    [pscustomobject]@{
        product = 'eMule Next 0.2.0 Preview 2'
        gitHead = $identity.head
        exeSha256 = $identity.exeSha256
        created = [DateTime]::Now.ToString('o')
        updated = [DateTime]::Now.ToString('o')
        checks = $items
    }
}

function Save-Record($record) {
    if (-not (Test-Path -LiteralPath $Artifacts -PathType Container)) {
        New-Item -ItemType Directory -Path $Artifacts | Out-Null
    }
    $record.updated = [DateTime]::Now.ToString('o')
    $json = $record | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($Record, $json, $Utf8NoBom)
}

function Load-Record {
    if (-not (Test-Path -LiteralPath $Record -PathType Leaf)) {
        throw "Acceptance record missing: $Record. Run with -Initialize first."
    }
    $json = [System.IO.File]::ReadAllText($Record, [System.Text.Encoding]::UTF8)
    $record = $json | ConvertFrom-Json
    $identity = Get-BuildIdentity
    if ($record.gitHead -ne $identity.head -or $record.exeSha256 -ne $identity.exeSha256) {
        throw "Acceptance record belongs to another build. Expected head/hash $($identity.head) / $($identity.exeSha256). Run -Initialize for this build."
    }
    return $record
}

function Find-Check($record, [string]$id) {
    $match = @($record.checks | Where-Object { $_.id -eq $id })
    if ($match.Count -ne 1) {
        $known = ($Checks | ForEach-Object { $_.id }) -join ', '
        throw "Unknown acceptance check '$id'. Known IDs: $known"
    }
    return $match[0]
}

function Set-Result([string]$id, [string]$result, [string]$note) {
    $record = Load-Record
    $check = Find-Check $record $id
    $check.status = $result
    $check.note = $note
    $check.updated = [DateTime]::Now.ToString('o')
    Save-Record $record
    Write-Host "$id -> $result"
}

function Show-Status($record) {
    Write-Host "Preview 2 runtime acceptance"
    Write-Host "Head: $($record.gitHead)"
    Write-Host "EXE : $($record.exeSha256)"
    Write-Host ''
    foreach ($check in $record.checks) {
        Write-Host ("{0,-18} {1,-10} {2}" -f $check.id, $check.status, $check.title)
        if (-not [string]::IsNullOrWhiteSpace([string]$check.note)) {
            Write-Host ("  note: {0}" -f $check.note)
        }
    }
}

function Verify-Group([string]$group) {
    $record = Load-Record
    $required = @($record.checks | Where-Object { $group -eq 'all' -or $_.group -eq $group })
    $notPass = @($required | Where-Object { $_.status -ne 'PASS' })
    if ($notPass.Count -gt 0) {
        Write-Host 'Acceptance is not complete:'
        foreach ($check in $notPass) {
            Write-Host (" - {0}: {1}" -f $check.id, $check.status)
        }
        throw "$($notPass.Count) required acceptance check(s) are not PASS."
    }
    Write-Host "Preview 2 $group runtime acceptance PASS for $($record.gitHead)"
}

if ($Initialize) {
    $record = New-Record
    Save-Record $record
    Write-Host "Initialized acceptance record: $Record"
    Show-Status $record
    exit 0
}

if ($PSCmdlet.ParameterSetName -eq 'Pass') {
    Set-Result $Pass 'PASS' $Note
    exit 0
}
if ($PSCmdlet.ParameterSetName -eq 'Fail') {
    Set-Result $Fail 'FAIL' $Note
    exit 0
}
if ($VerifyCore) {
    Verify-Group 'core'
    exit 0
}
if ($VerifyAll) {
    Verify-Group 'all'
    exit 0
}

$record = Load-Record
if ($Run) {
    foreach ($check in @($record.checks | Where-Object { $_.status -ne 'PASS' })) {
        Clear-Host
        Write-Host "[$($check.id)] $($check.title)"
        if (-not [string]::IsNullOrWhiteSpace([string]$check.note)) { Write-Host "Current note: $($check.note)" }
        Write-Host ''
        $answer = Read-Host 'Result: P=PASS, F=FAIL, S=skip, Q=quit'
        if ($answer -match '^[Qq]$') { break }
        if ($answer -match '^[Ss]$') { continue }
        if ($answer -match '^[Pp]$') {
            $check.status = 'PASS'
            $check.note = Read-Host 'Optional note'
            $check.updated = [DateTime]::Now.ToString('o')
            Save-Record $record
        }
        elseif ($answer -match '^[Ff]$') {
            $check.status = 'FAIL'
            $check.note = Read-Host 'Failure note'
            $check.updated = [DateTime]::Now.ToString('o')
            Save-Record $record
        }
    }
    Clear-Host
    Show-Status (Load-Record)
    exit 0
}

Show-Status $record
