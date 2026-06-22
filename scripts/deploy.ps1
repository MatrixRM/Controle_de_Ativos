# scripts/deploy.ps1
param(
    [switch]$NoRestart = $false
)

$projectDir = "C:\Users\roberto.manica\Desktop\ativos\Controle_de_Ativos"
$python = Join-Path $projectDir "env\Scripts\python.exe"
$log = Join-Path $projectDir "logs\deploy_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').log"

if (-not (Test-Path (Join-Path $projectDir "logs"))) {
    New-Item -ItemType Directory -Path (Join-Path $projectDir "logs") | Out-Null
}

Set-Location -LiteralPath $projectDir

"=== Deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" | Out-File -FilePath $log

Write-Host "[1/5] Atualizando código..."
git pull 2>&1 | Out-File -FilePath $log -Append

Write-Host "[2/5] Instalando dependências..."
& $python -m pip install -r requirements.txt 2>&1 | Out-File -FilePath $log -Append

Write-Host "[3/5] Rodando migrations..."
& $python manage.py migrate 2>&1 | Out-File -FilePath $log -Append

Write-Host "[4/5] Coletando arquivos estáticos..."
& $python manage.py collectstatic --noinput 2>&1 | Out-File -FilePath $log -Append

Write-Host "[5/5] Verificando sistema..."
& $python manage.py check --deploy 2>&1 | Out-File -FilePath $log -Append

if (-not $NoRestart) {
    Write-Host "[INFO] Reiniciando IIS..."
    iisreset 2>&1 | Out-File -FilePath $log -Append
}

Write-Host "[OK] Deploy concluído. Log: $log"
