Param([string[]]$Args)
# Launcher for Duck Hunt (PowerShell)
Write-Host "Installing dependencies (requirements.txt)..."
& python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
Write-Host "Starting Duck Hunt..."
& python (Join-Path $PSScriptRoot 'duck_hunt.py') @Args
Read-Host -Prompt "Press Enter to exit"
