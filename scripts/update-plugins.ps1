# Refresh only the already installed EROL marketplace and plugin.
[CmdletBinding()]
param(
    [ValidateSet('Codex', 'Claude', 'Both')][string]$Harness = 'Both',
    [switch]$Register,
    [switch]$Unregister
)
$ErrorActionPreference = 'Stop'
$taskName = 'EROL Plugin Updates'
$stateDirectory = Join-Path $env:USERPROFILE '.erol/updater'

if ($Unregister) {
    $ownedTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($ownedTask) {
        if ($ownedTask.Description -ne 'Refresh installed EROL plugins from their configured marketplace.') {
            throw 'Task name is owned by another application.'
        }
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    Write-Output 'EROL update task removed; plugins and project memory retained.'
    exit 0
}

if ($Register) {
    New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
    $savedScript = Join-Path $stateDirectory 'update-plugins.ps1'
    $taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($taskExists -and $taskExists.Description -ne 'Refresh installed EROL plugins from their configured marketplace.') {
        throw 'Task name is already owned by another application.'
    }
    Copy-Item -LiteralPath $PSCommandPath -Destination $savedScript -Force
    $clientPaths = @{}
    foreach ($clientName in @('codex', 'claude')) {
        $resolvedClient = Get-Command $clientName -ErrorAction SilentlyContinue
        if ($resolvedClient -and $resolvedClient.Source) { $clientPaths[$clientName] = $resolvedClient.Source }
    }
    $clientPaths | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stateDirectory 'clients.json') -Encoding UTF8
    # Persist the OS shell rather than a temporary shell bundled by an agent host.
    $executable = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
    $arguments = '-NoProfile -NonInteractive -WindowStyle Hidden -File "' + $savedScript + '" -Harness ' + $Harness
    $action = New-ScheduledTaskAction -Execute $executable -Argument $arguments -WorkingDirectory $stateDirectory
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $triggers = @(
        (New-ScheduledTaskTrigger -AtLogOn -User $identity),
        (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours 6))
    )
    $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggers -Principal $principal -Settings $settings -Description 'Refresh installed EROL plugins from their configured marketplace.' -Force | Out-Null
    Write-Output 'EROL updates enabled at login and every six hours while signed in.'
    exit 0
}

New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
$logPath = Join-Path $stateDirectory 'updates.log'
if ((Test-Path -LiteralPath $logPath) -and (Get-Item -LiteralPath $logPath).Length -gt 1MB) {
    Move-Item -LiteralPath $logPath -Destination (Join-Path $stateDirectory 'updates.previous.log') -Force
}
$failed = $false
$savedPaths = $null
$savedPathsFile = Join-Path $stateDirectory 'clients.json'
if (Test-Path -LiteralPath $savedPathsFile) { $savedPaths = Get-Content -LiteralPath $savedPathsFile -Raw | ConvertFrom-Json }
foreach ($client in @('Codex', 'Claude')) {
    if ($Harness -ne 'Both' -and $Harness -ne $client) { continue }
    try {
        $clientName = $client.ToLowerInvariant()
        $resolvedClient = Get-Command $clientName -ErrorAction SilentlyContinue
        $clientExecutable = if ($resolvedClient) { $resolvedClient.Source } else { $savedPaths.$clientName }
        if (-not $clientExecutable -or -not (Test-Path -LiteralPath $clientExecutable -PathType Leaf)) {
            throw "$client CLI is unavailable; register again after installing or moving it."
        }
        $commands = if ($client -eq 'Codex') {
            @(@('plugin', 'marketplace', 'upgrade', 'erol'), @('plugin', 'add', 'erol@erol'))
        } else {
            @(@('plugin', 'marketplace', 'update', 'erol'), @('plugin', 'update', 'erol@erol'))
        }
        foreach ($clientArguments in $commands) {
            $result = & $clientExecutable @clientArguments 2>&1
            if ($LASTEXITCODE -ne 0) { throw "$client update exited with $LASTEXITCODE" }
            $result | Add-Content -LiteralPath $logPath -Encoding UTF8
        }
        ('{0:o} {1}: EROL refreshed; start a new session to load the version.' -f (Get-Date), $client) | Add-Content -LiteralPath $logPath -Encoding UTF8
    } catch {
        $failed = $true
        ('{0:o} {1}: update failed; check marketplace configuration and client availability.' -f (Get-Date), $client) | Add-Content -LiteralPath $logPath -Encoding UTF8
        Write-Warning "$client update failed: $($_.Exception.Message)"
    }
}
if ($failed) { exit 1 }
Write-Output 'Installed EROL plugins refreshed. Start a new session to load the update.'
