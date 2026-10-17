# PowerShell wrapper (Windows): pwsh .\scripts\dwr.ps1 <command> [options]
# Uses the Python launcher in isolated mode. Private stages need $env:DWR_PRIVATE_ROOT.
param([Parameter(ValueFromRemainingArguments = $true)] [string[]] $Arguments)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$script = Join-Path $PSScriptRoot 'dwr.py'
$python = (Get-Command python -ErrorAction Stop).Source
& $python -I $script @Arguments
exit $LASTEXITCODE
