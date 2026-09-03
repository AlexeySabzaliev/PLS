# Ежедневный бэкап БД ПЛС (Windows Task Scheduler / ручной запуск)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$LogDir = $env:PLS_BACKUP_DIR
if (-not $LogDir) { $LogDir = "backups" }
if (-not [System.IO.Path]::IsPathRooted($LogDir)) {
    $LogDir = Join-Path $Root $LogDir
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir "backup.log"

function Write-Log([string]$Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

Write-Log "=== backup start ==="

if (Test-Path (Join-Path $Root ".env")) {
    Get-Content (Join-Path $Root ".env") | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

$Retention = $env:PLS_BACKUP_RETENTION
$BackupArgs = @("pls", "backup")
if ($Retention) {
    $BackupArgs += @("--retention", $Retention)
}

$flask = Get-Command flask -ErrorAction SilentlyContinue
if (-not $flask) {
    Write-Log "ERROR: flask not found in PATH"
    exit 1
}

& flask @BackupArgs
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: flask pls backup failed with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Log "=== backup ok ==="
exit 0
