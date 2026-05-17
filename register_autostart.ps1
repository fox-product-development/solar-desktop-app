# register_autostart.ps1 — v2, simplified for broader PowerShell compatibility
# Run from an elevated (Run as Administrator) PowerShell prompt.

$TaskName   = "SolarMonitor"
$ProjectDir = "A:\Personal coding\Solar Desktop App"
$VbsPath    = Join-Path $ProjectDir "launch_solar.vbs"

if (-not (Test-Path $VbsPath)) {
    Write-Error "launch_solar.vbs not found at: $VbsPath"
    exit 1
}

# Remove existing task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Action: run the VBS silently via wscript
$Action = New-ScheduledTaskAction `
    -Execute "wscript.exe" `
    -Argument "`"$VbsPath`"" `
    -WorkingDirectory $ProjectDir

# Trigger: at logon for current user, 30-second delay
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Trigger.Delay = "PT30S"

# Register with minimal settings for compatibility
Register-ScheduledTask `
    -TaskName    $TaskName `
    -Action      $Action `
    -Trigger     $Trigger `
    -RunLevel    Limited `
    -Description "Starts Solar Monitor desktop widget on login." `
    -Force

Write-Host ""
Write-Host "Verify with: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan