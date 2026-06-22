<#
.SYNOPSIS
    Registra a tarefa agendada "Inventario Ativos - Info Rede" (a cada 2 dias).
.DESCRIPTION
    Cria uma tarefa que executa `python manage.py atualizar_info_rede` a cada 2 dias.
    Requer execução como Administrador.
.NOTES
    Autor: Equipe de TI
    Requer: PowerShell 5.1+ como Administrador
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ProjectDir = "$PSScriptRoot\..",

    [Parameter(Mandatory=$false)]
    [string]$TaskName = "Inventario Ativos - Info Rede",

    [Parameter(Mandatory=$false)]
    [string]$Hora = "05:00"
)

# Verifica se é administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERRO: Execute como Administrador!" -ForegroundColor Red
    exit 1
}

$ProjectDir = Resolve-Path $ProjectDir
$PythonPath = "$ProjectDir\env\Scripts\python.exe"
$ManagePy = "$ProjectDir\manage.py"

if (-not (Test-Path $PythonPath)) {
    Write-Host "ERRO: Python não encontrado em $PythonPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ManagePy)) {
    Write-Host "ERRO: manage.py não encontrado em $ManagePy" -ForegroundColor Red
    exit 1
}

# Monta a action
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "manage.py atualizar_info_rede --ad-sync" -WorkingDirectory $ProjectDir

# Principal como SYSTEM
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Settings: até 4h de execução
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 4)

Write-Host "Registrando tarefa '$TaskName'..." -ForegroundColor Cyan

try {
    # Cria a tarefa com trigger diário (depois ajustamos o intervalo)
    $trigger = New-ScheduledTaskTrigger -Daily -At $Hora
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

    # Ajusta o XML para intervalo de 2 dias
    $task = Get-ScheduledTask -TaskName $TaskName
    $xml = [xml]($task | Export-ScheduledTask)
    $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
    $ns.AddNamespace("ns", "http://schemas.microsoft.com/windows/2004/02/mit/task")

    $dayNode = $xml.SelectSingleNode("//ns:ScheduleByDay", $ns)
    if ($dayNode) {
        # Remove qualquer DaysInterval existente
        $old = $dayNode.SelectSingleNode("ns:DaysInterval", $ns)
        if ($old) { [void]$dayNode.RemoveChild($old) }
        # Cria novo com intervalo 2
        $intervalNode = $xml.CreateElement("DaysInterval", "http://schemas.microsoft.com/windows/2004/02/mit/task")
        $intervalNode.InnerText = "2"
        $dayNode.AppendChild($intervalNode) | Out-Null
    }

    $xml.OuterXml | Set-ScheduledTask -TaskName $TaskName

    Write-Host "`nTarefa registrada com sucesso!" -ForegroundColor Green
    Write-Host "  Nome: $TaskName" -ForegroundColor Gray
    Write-Host "  Comando: $PythonPath manage.py atualizar_info_rede" -ForegroundColor Gray
    Write-Host "  Diretório: $ProjectDir" -ForegroundColor Gray
    Write-Host "  Horário: $Hora (a cada 2 dias)" -ForegroundColor Gray
    Write-Host "  Usuário: SYSTEM" -ForegroundColor Gray

    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State, Triggers, Actions
} catch {
    Write-Host "ERRO ao registrar tarefa: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
