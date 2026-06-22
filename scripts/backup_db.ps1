# scripts/backup_db.ps1
param(
    [string]$BackupDir = "C:\Users\roberto.manica\Desktop\ativos\backups"
)

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$dbPath = "C:\Users\roberto.manica\Desktop\ativos\Controle_de_Ativos\db.sqlite3"
$backupFile = Join-Path -Path $BackupDir -ChildPath "db_$timestamp.sqlite3"

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

Copy-Item -LiteralPath $dbPath -Destination $backupFile -Force
Write-Host "[OK] Backup criado: $backupFile"

# Manter apenas os 7 backups mais recentes
$backups = Get-ChildItem -Path $BackupDir -Filter "db_*.sqlite3" | Sort-Object Name -Descending
if ($backups.Count -gt 7) {
    $backups | Select-Object -Skip 7 | Remove-Item -Force
    Write-Host "[OK] Backups antigos removidos"
}
