param(
    [string]$RepoPath = (Resolve-Path "$PSScriptRoot\..").Path,
    [string]$PythonPath = "",
    [string]$TaskName = "ResearchWikiGitAutoSync",
    [int]$IntervalMinutes = 30
)

if (-not $PythonPath) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $PythonPath = $pythonCommand.Source
    }
}

if (-not $PythonPath) {
    $python3Command = Get-Command python3 -ErrorAction SilentlyContinue
    if ($python3Command) {
        $PythonPath = $python3Command.Source
    }
}

if (-not $PythonPath) {
    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        $PythonPath = $pyCommand.Source
    }
}

if (-not $PythonPath) {
    throw "Python was not found. Re-run with -PythonPath `"C:\path\to\python.exe`"."
}

$script = Join-Path $RepoPath "tools\git_auto_sync.py"
if ((Split-Path $PythonPath -Leaf) -eq "py.exe") {
    $argument = "-3 `"$script`" sync"
} else {
    $argument = "`"$script`" sync"
}
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument $argument -WorkingDirectory $RepoPath
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Auto sync Research Wiki with GitHub." -Force
Write-Host "Installed scheduled task '$TaskName' for $RepoPath every $IntervalMinutes minutes."
