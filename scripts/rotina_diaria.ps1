# scripts/rotina_diaria.ps1
$projectDir = "C:\Users\roberto.manica\Desktop\ativos\Controle_de_Ativos"
$python = Join-Path -Path $projectDir -ChildPath "env\Scripts\python.exe"
$log = Join-Path -Path $projectDir -ChildPath "logs\rotina_$(Get-Date -Format 'yyyy-MM-dd').log"

if (-not (Test-Path (Join-Path $projectDir "logs"))) {
    New-Item -ItemType Directory -Path (Join-Path $projectDir "logs") | Out-Null
}

Set-Location -LiteralPath $projectDir

"=== Rotina Diária $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $log

Write-Host "[1/3] Gerando notificações..."
& $python manage.py gerar_notificacoes 2>&1 | Out-File -FilePath $log -Append

Write-Host "[2/3] Verificando preventivas..."
& $python manage.py verificar_preventivas 2>&1 | Out-File -FilePath $log -Append

Write-Host "[3/3] Atualizando informações de rede..."
& $python manage.py atualizar_info_rede --ad-sync 2>&1 | Out-File -FilePath $log -Append

Write-Host "[OK] Rotina concluída. Log: $log"
