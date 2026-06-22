# scripts/registrar_tarefas.ps1
$projectDir = "C:\Users\roberto.manica\Desktop\ativos\Controle_de_Ativos"
$python = Join-Path $projectDir "env\Scripts\python.exe"
$rotinaScript = Join-Path $projectDir "scripts\rotina_diaria.ps1"
$backupScript = Join-Path $projectDir "scripts\backup_db.ps1"

Write-Host "Registrando tarefa: Rotina Diária (06:00)..."
schtasks /CREATE /TN "ControleAtivos\RotinaDiaria" /SC DAILY /ST 06:00 /TR "powershell.exe -File \"$rotinaScript\"" /F /RU SYSTEM

Write-Host "Registrando tarefa: Backup Semanal (domingo 22:00)..."
schtasks /CREATE /TN "ControleAtivos\BackupSemanal" /SC WEEKLY /D SUN /ST 22:00 /TR "powershell.exe -File \"$backupScript\"" /F /RU SYSTEM

Write-Host ""
Write-Host "Tarefas registradas. Verifique com: schtasks /QUERY /TN ControleAtivos\*"
