<#
.SYNOPSIS
    Coleta inventário de computadores do Active Directory e envia para API Django.
.DESCRIPTION
    - Busca computadores no AD com Get-ADComputer
    - Testa conectividade com Test-Connection
    - Coleta dados via CIM/WMI (Win32_ComputerSystem, Win32_BIOS, Win32_OperatingSystem, Win32_Processor)
    - Envia JSON para a API /api/ativos/sync/
    - Gera log em C:\Inventario\sync_ativos.log
.NOTES
    Autor: Equipe de TI
    Requer: PowerShell 5.1+, módulo ActiveDirectory, permissão de admin local e remoto (CIM/WMI)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiUrl,
    [Parameter(Mandatory=$true)]
    [string]$Token,
    [Parameter(Mandatory=$false)]
    [int]$TimeoutSegundos = 30,
    [Parameter(Mandatory=$false)]
    [string]$LogPath = "C:\Inventario\sync_ativos.log",
    [Parameter(Mandatory=$false)]
    [string[]]$Computadores = $null,
    [Parameter(Mandatory=$false)]
    [switch]$Rapido
)

# Garante diretório de log
$LogDir = Split-Path $LogPath -Parent
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] [$Level] $Message"
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Get-ComputerInventory {
    param([string]$ComputerName)

    $result = @{
        nome              = $ComputerName.ToUpper()
        ip                = $null
        usuario           = ""
        fabricante        = ""
        modelo             = ""
        serial            = ""
        processador       = ""
        memoria_gb        = $null
        sistema           = ""
        ultimo_logon      = $null
        status_rede       = "offline"
    }

    if ($Rapido) {
        $ping = Test-Connection -ComputerName $ComputerName -Count 1 -Quiet -ErrorAction SilentlyContinue
        if (-not $ping) {
            Write-Log "Computador $ComputerName offline (rápido)" "WARN"
            return $result
        }
        try {
            $session = New-CimSession -ComputerName $ComputerName -ErrorAction Stop -OperationTimeoutSec 3
        } catch {
            Write-Log "Falha CIM em $ComputerName (rápido)" "WARN"
            return $result
        }
    } else {
        $ping = Test-Connection -ComputerName $ComputerName -Count 2 -Quiet -ErrorAction SilentlyContinue
        if (-not $ping) {
            Write-Log "Computador $ComputerName offline" "WARN"
            return $result
        }
        try {
            $session = New-CimSession -ComputerName $ComputerName -ErrorAction Stop -OperationTimeoutSec 10
        } catch {
            Write-Log "Falha ao criar sessão CIM em $ComputerName : $($_.Exception.Message)" "WARN"
            return $result
        }
    }

    try {
        # IP (primeiro adaptador IPv4 não loopback)
        $net = Get-CimInstance -CimSession $session -ClassName Win32_NetworkAdapterConfiguration -Filter "IPEnabled = True" -ErrorAction SilentlyContinue
        $ipv4 = $net | Where-Object { $_.IPAddress -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1
        if ($ipv4) {
            $result.ip = ($ipv4.IPAddress | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' }) | Select-Object -First 1
        }

        # Sistema
        $cs = Get-CimInstance -CimSession $session -ClassName Win32_ComputerSystem -ErrorAction SilentlyContinue
        if ($cs) {
            $result.fabricante  = $cs.Manufacturer
            $result.modelo      = $cs.Model
            $result.usuario     = $cs.UserName
            $result.memoria_gb  = [math]::Round($cs.TotalPhysicalMemory / 1GB)
        }

        # BIOS / Serial
        $bios = Get-CimInstance -CimSession $session -ClassName Win32_BIOS -ErrorAction SilentlyContinue
        if ($bios) {
            $rawSerial = ($bios.SerialNumber -replace '\s', '').Trim()
            if ($rawSerial -notmatch '^(0+|ToBeFilledByOEM|SystemSerialNumber|NotSpecified|None|)$') {
                $result.serial = $rawSerial
            }
        }

        # Processador
        $cpu = Get-CimInstance -CimSession $session -ClassName Win32_Processor -ErrorAction SilentlyContinue
        if ($cpu) {
            $result.processador = "$($cpu.Name)" -replace '\s+', ' '
        }

        # Sistema Operacional
        $os = Get-CimInstance -CimSession $session -ClassName Win32_OperatingSystem -ErrorAction SilentlyContinue
        if ($os) {
            $result.sistema = "$($os.Caption) $($os.OSArchitecture)" -replace '\s+', ' '
            $result.ultimo_logon = $os.LastBootUpTime.ToString("yyyy-MM-ddTHH:mm:sszzz")
        }
        # NOTA: ultimo_logon armazena a última inicialização (LastBootUpTime), não o logon do usuário.
        # Para obter o logon real seria necessário Win32_NetworkLoginProfile, que é mais lento.

        $result.status_rede = "online"
        Write-Log "Dados coletados de $ComputerName" "INFO"
    } catch {
        Write-Log "Erro ao consultar $ComputerName : $($_.Exception.Message)" "ERROR"
    } finally {
        Remove-CimSession -CimSession $session -ErrorAction SilentlyContinue
    }

    return $result
}

# ===== INÍCIO =====
Write-Log "=== Início da sincronização de ativos ==="

# Se não foram passados computadores via parâmetro, busca no AD
if (-not $Computadores -or $Computadores.Count -eq 0) {
    $adModule = Get-Module -ListAvailable -Name ActiveDirectory
    if (-not $adModule) {
        Write-Log "Módulo ActiveDirectory não disponível. Informe -Computadores manualmente." "ERROR"
        exit 1
    }

    try {
        Import-Module ActiveDirectory -ErrorAction Stop
    } catch {
        Write-Log "Falha ao importar ActiveDirectory: $($_.Exception.Message)" "ERROR"
        exit 1
    }

    try {
        $Computadores = Get-ADComputer -Filter * -Properties Name, OperatingSystem | Select-Object -ExpandProperty Name
        Write-Log "$($Computadores.Count) computadores encontrados no AD" "INFO"
    } catch {
        Write-Log "Falha ao consultar AD: $($_.Exception.Message)" "ERROR"
        exit 1
    }
} else {
    Write-Log "Usando $($Computadores.Count) computador(es) informado(s) via parâmetro" "INFO"
}

$inventario = @()
$total = $computadores.Count
$i = 0
$batchSize = 50

function Send-Batch {
    param([array]$Batch)
    if ($Batch.Count -eq 0) { return }
    $body = $Batch | ConvertTo-Json -Depth 3
    try {
        $response = Invoke-RestMethod -Uri $ApiUrl -Method Post -Headers @{
            "Authorization" = "Token $Token"
            "Content-Type"  = "application/json; charset=utf-8"
        } -Body $body -TimeoutSec $TimeoutSegundos -ErrorAction Stop
        Write-Log "Lote enviado: criados=$($response.criados) atualizados=$($response.atualizados) erros=$($response.erros.Count)" "INFO"
        if ($response.erros -and $response.erros.Count -gt 0) {
            foreach ($e in $response.erros) {
                Write-Log "Erro no lote: $($e.erro)" "ERROR"
            }
        }
    } catch {
        Write-Log "Falha ao enviar lote: $($_.Exception.Message)" "ERROR"
    }
}

foreach ($comp in $computadores) {
    $i++
    Write-Progress -Activity "Coletando inventário" -Status "$comp ($i de $total)" -PercentComplete (($i / $total) * 100)
    Write-Log "Processando $comp..." "INFO"

    $dados = Get-ComputerInventory -ComputerName $comp
    $inventario += $dados

    if ($inventario.Count -ge $batchSize) {
        Send-Batch -Batch $inventario
        $inventario = @()
    }
}

Write-Progress -Activity "Coletando inventário" -Completed

# Envia lote restante
if ($inventario.Count -gt 0) {
    Send-Batch -Batch $inventario
}

Write-Log "=== Sincronização concluída ==="
