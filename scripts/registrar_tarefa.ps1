<#
.SYNOPSIS
    Registra a tarefa agendada "Inventario Ativos - Sincronizacao" no Windows Task Scheduler.
.DESCRIPTION
    Cria uma tarefa diária que executa o script sync_ativos.ps1 às 22:00.
    Requer execução como Administrador.
.NOTES
    Autor: Equipe de TI
    Requer: PowerShell 5.1+ como Administrador
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiUrl,

    [Parameter(Mandatory=$true)]
    [string]$Token,

    [Parameter(Mandatory=$false)]
    [string]$ScriptPath = "$PSScriptRoot\sync_ativos.ps1",

    [Parameter(Mandatory=$false)]
    [string]$TaskName = "Inventario Ativos - Sincronizacao",

    [Parameter(Mandatory=$false)]
    [string]$Hora = "22:00"
)

# Verifica se é administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERRO: Execute como Administrador!" -ForegroundColor Red
    exit 1
}

# Verifica se o script existe
if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERRO: Script não encontrado em $ScriptPath" -ForegroundColor Red
    exit 1
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$ScriptPath`" -ApiUrl `"$ApiUrl`" -Token `"$Token`""

$trigger = New-ScheduledTaskTrigger -Daily -At $Hora

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
    Write-Host "Tarefa '$TaskName' registrada com sucesso!" -ForegroundColor Green
    Write-Host "  Script: $ScriptPath" -ForegroundColor Gray
    Write-Host "  API: $ApiUrl" -ForegroundColor Gray
    Write-Host "  Horário: $Hora (diário)" -ForegroundColor Gray
    Write-Host "  Usuário: SYSTEM" -ForegroundColor Gray
} catch {
    Write-Host "ERRO ao registrar tarefa: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
