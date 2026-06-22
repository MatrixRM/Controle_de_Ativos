import subprocess
import re
import os
import tempfile

from django.core.management.base import BaseCommand
from core.models import Equipamento
from core.mapeamento_empresas import detectar_empresa_por_hostname


POWERSHELL_SCRIPT = r'''
param([string]$Hostname)
try {
    $cim = New-CimSession -ComputerName $Hostname -ErrorAction Stop -OperationTimeoutSec 10

    # --- REDE ---
    $ip = $null
    $macEth = $null
    $macWifi = $null

    $net = Get-CimInstance -CimSession $cim -ClassName Win32_NetworkAdapterConfiguration -Filter "IPEnabled = True" -ErrorAction SilentlyContinue
    foreach ($cfg in $net) {
        $mac = $cfg.MACAddress
        $desc = "$($cfg.Description)"
        $firstIp = ($cfg.IPAddress | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' }) | Select-Object -First 1
        if ($firstIp -and -not $ip) { $ip = $firstIp }
        if ($desc -match 'Wireless|Wi-Fi|802\.11|WLAN|Wireless LAN') {
            if (-not $macWifi) { $macWifi = $mac }
        } else {
            if (-not $macEth) { $macEth = $mac }
        }
    }

    # --- TEAMVIEWER ---
    $tvId = $null
    foreach ($key in @("SOFTWARE\TeamViewer", "SOFTWARE\WOW6432Node\TeamViewer")) {
        $r = Invoke-CimMethod -CimSession $cim -Namespace root\default -ClassName StdRegProv -MethodName GetDWORDValue -Arguments @{
            hDefKey = [uint32]2147483650
            sSubKeyName = $key
            sValueName = "ClientID"
        } -ErrorAction SilentlyContinue
        if ($r.uValue) { $tvId = "$($r.uValue)"; break }
    }

    # --- SISTEMA OPERACIONAL ---
    $osCaption = $null
    $osVersion = $null
    $os = Get-CimInstance -CimSession $cim -ClassName Win32_OperatingSystem -ErrorAction SilentlyContinue
    if ($os) {
        $osCaption = $os.Caption
        $osVersion = $os.Version
    }

    # --- FABRICANTE E MODELO ---
    $fabricante = $null
    $modelo = $null
    $cs = Get-CimInstance -CimSession $cim -ClassName Win32_ComputerSystem -ErrorAction SilentlyContinue
    if ($cs) {
        $fabricante = $cs.Manufacturer
        $modelo = $cs.Model
    }

    # --- SERIAL ---
    $serial = $null
    $bios = Get-CimInstance -CimSession $cim -ClassName Win32_BIOS -ErrorAction SilentlyContinue
    if ($bios) {
        $raw = ($bios.SerialNumber -replace '\s', '').Trim()
        if ($raw -notmatch '^(0+|ToBeFilledByOEM|SystemSerialNumber|NotSpecified|None|)$') {
            $serial = $raw
        }
    }

    # --- ÚLTIMO USUÁRIO LOGADO ---
    $ultimoUsuario = $null
    $reg = Invoke-CimMethod -CimSession $cim -Namespace root\default -ClassName StdRegProv -MethodName GetStringValue -Arguments @{
        hDefKey = [uint32]2147483650
        sSubKeyName = "SOFTWARE\Microsoft\Windows\CurrentVersion\Authentication\LogonUI"
        sValueName = "LastLoggedOnUser"
    } -ErrorAction SilentlyContinue
    if ($reg.sValue) { $ultimoUsuario = $reg.sValue }

    # --- VERSÃO DO OFFICE ---
    $officeVer = $null
    $officePaths = @(
        @{p="SOFTWARE\Microsoft\Office\ClickToRun\Configuration"; v="ClientVersionToReport"},
        @{p="SOFTWARE\Microsoft\Office\ClickToRun\Configuration"; v="VersionToReport"},
        @{p="SOFTWARE\Microsoft\Office\16.0\Common\ProductVersion"; v="LastProductVersion"},
        @{p="SOFTWARE\Microsoft\Office\15.0\Common\ProductVersion"; v="LastProductVersion"},
        @{p="SOFTWARE\WOW6432Node\Microsoft\Office\ClickToRun\Configuration"; v="ClientVersionToReport"},
        @{p="SOFTWARE\WOW6432Node\Microsoft\Office\16.0\Common\ProductVersion"; v="LastProductVersion"}
    )
    foreach ($entry in $officePaths) {
        $r = Invoke-CimMethod -CimSession $cim -Namespace root\default -ClassName StdRegProv -MethodName GetStringValue -Arguments @{
            hDefKey = [uint32]2147483650
            sSubKeyName = $entry.p
            sValueName = $entry.v
        } -ErrorAction SilentlyContinue
        if ($r.sValue) { $officeVer = $r.sValue; break }
    }

    Remove-CimSession -CimSession $cim -ErrorAction SilentlyContinue
    Write-Output ('IP=' + $ip + '|TV=' + $tvId + '|MAC_ETH=' + $macEth + '|MAC_WIFI=' + $macWifi + '|SO=' + $osCaption + '|VER_SO=' + $osVersion + '|VER_OFFICE=' + $officeVer + '|FAB=' + $fabricante + '|MOD=' + $modelo + '|SERIAL=' + $serial + '|USUARIO=' + $ultimoUsuario)
} catch {
    Write-Output 'IP=|TV=|MAC_ETH=|MAC_WIFI=|SO=|VER_SO=|VER_OFFICE=|FAB=|MOD=|SERIAL=|USUARIO='
}
'''

AD_QUERY_SCRIPT = r'''
$module = Get-Module -ListAvailable -Name ActiveDirectory
if (-not $module) { Write-Output 'ERRO:Modulo AD nao disponivel'; exit 1 }
Import-Module ActiveDirectory -ErrorAction Stop
$comps = Get-ADComputer -Filter { Enabled -eq $true } -Properties Name, OperatingSystem | Select-Object -ExpandProperty Name
Write-Output ($comps -join '|||')
'''


class Command(BaseCommand):
    help = 'Busca IP, MAC, TeamViewer, SO e Office dos equipamentos via CIM/PowerShell'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ps_file = None

    def _get_ps_file(self):
        if self._ps_file is None:
            fd, path = tempfile.mkstemp(suffix='.ps1', prefix='info_rede_', text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(POWERSHELL_SCRIPT)
            self._ps_file = path
        return self._ps_file

    def add_arguments(self, parser):
        parser.add_argument('--hostname', help='Buscar apenas um hostname específico')
        parser.add_argument('--dry-run', action='store_true', help='Apenas exibe o que seria atualizado')
        parser.add_argument('--ad-sync', action='store_true', help='Sincroniza computadores do AD com o banco')

    def _exec_ps(self, script, args=None):
        fd, path = tempfile.mkstemp(suffix='.ps1', prefix='ps_', text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(script)
        cmd = ['powershell', '-NoProfile', '-File', path]
        if args:
            cmd.extend(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        os.unlink(path)
        return result

    def _buscar_ad(self):
        result = self._exec_ps(AD_QUERY_SCRIPT)
        if result.returncode != 0:
            erro = result.stdout.strip() or result.stderr.strip()
            raise RuntimeError(f'Falha ao consultar AD: {erro}')
        return [c.strip() for c in result.stdout.strip().split('|||') if c.strip()]

    def _buscar_info(self, hostname):
        ps_file = self._get_ps_file()
        result = subprocess.run(
            ['powershell', '-NoProfile', '-File', ps_file, '-Hostname', hostname],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.strip().splitlines():
            m = re.match(
                r'^IP=(.*)\|TV=(.*)\|MAC_ETH=(.*)\|MAC_WIFI=(.*)\|SO=(.*)\|VER_SO=(.*)\|VER_OFFICE=(.*)\|FAB=(.*)\|MOD=(.*)\|SERIAL=(.*)\|USUARIO=(.*)$',
                line.strip()
            )
            if m:
                return {
                    'ip': m.group(1) or None,
                    'tv_id': m.group(2) or None,
                    'mac_eth': m.group(3) or None,
                    'mac_wifi': m.group(4) or None,
                    'os_caption': m.group(5) or None,
                    'os_version': m.group(6) or None,
                    'office_ver': m.group(7) or None,
                    'fabricante': m.group(8) or None,
                    'modelo': m.group(9) or None,
                    'serial': m.group(10) or None,
                    'ultimo_usuario': m.group(11) or None,
                }
        return None

    def _sincronizar_ad(self, dry_run):
        self.stdout.write('Consultando Active Directory... ')
        self.stdout.flush()
        try:
            ad_computers = self._buscar_ad()
        except RuntimeError as e:
            self.stdout.write(self.style.ERROR(f'{e}'))
            return []
        self.stdout.write(self.style.SUCCESS(f'{len(ad_computers)} computadores encontrados'))

        existing = set(
            Equipamento.objects.filter(tipo__in=['DESKTOP', 'NOTEBOOK'])
            .values_list('numero_imobilizado', flat=True)
        )
        existing = {h.strip().upper() for h in existing if h}

        novos = [c for c in ad_computers if c.upper() not in existing]
        if not novos:
            self.stdout.write('Nenhum computador novo encontrado.')
            return []

        self.stdout.write(f'{len(novos)} novo(s) computador(es) para cadastrar:')
        criados = 0
        for hostname in novos:
            self.stdout.write(f'  {hostname}... ', ending='')
            self.stdout.flush()

            info = self._buscar_info(hostname)
            if not info:
                self.stdout.write(self.style.WARNING('offline'))

                if not dry_run:
                    Equipamento.objects.create(
                        numero_imobilizado=hostname.upper(),
                        tipo='DESKTOP',
                        marca='A Definir',
                        modelo='A Definir',
                        local=hostname.split('-')[0].strip(),
                        setor='A Definir',
                        empresa_id=detectar_empresa_por_hostname(hostname),
                    )
                    self.stdout.write(self.style.SUCCESS('cadastrado (offline)'))
                else:
                    self.stdout.write(self.style.WARNING('[DRY-RUN] seria cadastrado'))
                criados += 1
                continue

            empresa_id = detectar_empresa_por_hostname(hostname)
            fabricante = info['fabricante'] or 'A Definir'
            modelo = info['modelo'] or 'A Definir'
            serial = info['serial'] or ''

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'[DRY-RUN] fab={fabricante} mod={modelo} '
                    f'ip={info["ip"] or "—"} tv={info["tv_id"] or "—"}'
                ))
                criados += 1
                continue

            eq = Equipamento(
                numero_imobilizado=hostname.upper(),
                tipo='DESKTOP',
                marca=fabricante,
                modelo=modelo,
                local=hostname.split('-')[0].strip(),
                setor='A Definir',
                numero_serie=serial,
                empresa_id=empresa_id,
                ip=info['ip'],
                teamviewer_id=info['tv_id'],
                mac_ethernet=info['mac_eth'],
                mac_wifi=info['mac_wifi'],
                ultimo_usuario=info['ultimo_usuario'] or '',
                sistema_operacional=info['os_caption'] or '',
                versao_so=info['os_version'] or '',
                versao_office=info['office_ver'] or '',
            )
            eq.save()
            self.stdout.write(self.style.SUCCESS(
                f'cadastrado (ip={info["ip"] or "—"} tv={info["tv_id"] or "—"})'
            ))
            criados += 1

        return ad_computers

    def handle(self, *args, **options):
        hostname_filter = options.get('hostname')
        dry_run = options.get('dry_run')
        ad_sync = options.get('ad_sync')

        all_computers = None

        if ad_sync:
            self.stdout.write('--- Sincronizando com Active Directory ---')
            all_computers = self._sincronizar_ad(dry_run)
            if hostname_filter:
                all_computers = [h for h in all_computers if h.upper() == hostname_filter.upper()]

        if hostname_filter:
            qs = Equipamento.objects.filter(tipo__in=['DESKTOP', 'NOTEBOOK'])
            qs = qs.filter(numero_imobilizado__iexact=hostname_filter)
        elif all_computers:
            qs = Equipamento.objects.filter(
                tipo__in=['DESKTOP', 'NOTEBOOK'],
                numero_imobilizado__in=[c.upper() for c in all_computers],
            )
        else:
            qs = Equipamento.objects.filter(tipo__in=['DESKTOP', 'NOTEBOOK'])

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('Nenhum equipamento Desktop/Notebook para atualizar.'))
            self._limpar_ps_file()
            return

        self.stdout.write(f'\n--- Atualizando informações de rede para {total} equipamento(s) ---\n')

        atualizados = 0
        erros = 0

        for eq in qs:
            hostname = eq.numero_imobilizado.strip().upper()
            self.stdout.write(f'  {hostname}... ', ending='')
            self.stdout.flush()

            try:
                info = self._buscar_info(hostname)
            except subprocess.TimeoutExpired:
                self.stdout.write(self.style.ERROR('timeout'))
                if eq.status != 'OFFLINE':
                    eq.status = 'OFFLINE'
                    eq.save(update_fields=['status'])
                erros += 1
                continue

            if not info:
                self.stdout.write(self.style.WARNING('offline'))
                if eq.status != 'OFFLINE':
                    eq.status = 'OFFLINE'
                    eq.save(update_fields=['status'])
                continue

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'[DRY-RUN] ip={info["ip"] or "—"} tv={info["tv_id"] or "—"} '
                    f'so={info["os_caption"] or "—"} office={info["office_ver"] or "—"}'
                ))
                continue

            changed = False
            if eq.status != 'ATIVO':
                eq.status = 'ATIVO'
                changed = True
            for field, key in [
                ('ip', 'ip'),
                ('teamviewer_id', 'tv_id'),
                ('mac_ethernet', 'mac_eth'),
                ('mac_wifi', 'mac_wifi'),
                ('sistema_operacional', 'os_caption'),
                ('versao_so', 'os_version'),
                ('versao_office', 'office_ver'),
                ('ultimo_usuario', 'ultimo_usuario'),
            ]:
                val = info[key]
                if val and getattr(eq, field) != val:
                    setattr(eq, field, val)
                    changed = True

            if changed:
                eq.save(update_fields=[
                    'status', 'ip', 'teamviewer_id', 'mac_ethernet', 'mac_wifi',
                    'sistema_operacional', 'versao_so', 'versao_office',
                    'ultimo_usuario',
                ])
                self.stdout.write(self.style.SUCCESS(
                    f'ip={info["ip"] or "—"} tv={info["tv_id"] or "—"} '
                    f'so={info["os_caption"] or "—"} office={info["office_ver"] or "—"}'
                ))
                atualizados += 1
            else:
                self.stdout.write('sem alterações')

            sigla = hostname.split('-')[0].strip()
            if sigla and eq.local != sigla:
                eq.local = sigla
                eq.save(update_fields=['local'])
                self.stdout.write(self.style.SUCCESS(f'  local -> {sigla}'))

            usuario_str = info.get('ultimo_usuario')
            if usuario_str:
                username = usuario_str.rsplit('\\', 1)[-1].strip()
                if username and eq.responsavel != username:
                    eq.responsavel = username
                    eq.save(update_fields=['responsavel'])
                    self.stdout.write(self.style.SUCCESS(f'  responsavel -> {username}'))

        self.stdout.write(self.style.SUCCESS(f'\nConcluído: {atualizados} atualizados, {erros} erro(s)'))
        self._limpar_ps_file()

    def _limpar_ps_file(self):
        if self._ps_file and os.path.exists(self._ps_file):
            try:
                os.unlink(self._ps_file)
            except OSError:
                pass
            self._ps_file = None
