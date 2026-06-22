import json
import re
import subprocess
import unicodedata
from collections import Counter
from datetime import date, timedelta
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from .models import Equipamento, Empresa, Manutencao


def _get_gemini_client():
    key = settings.GEMINI_API_KEY
    if not key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except ImportError:
        return None


def _sistema_prompt():
    tipos = dict(Equipamento.TIPOS)
    status = dict(Equipamento.STATUS)
    empresas = list(Empresa.objects.values_list('nome', flat=True))
    setores = list(
        Equipamento.objects.exclude(setor='')
        .values_list('setor', flat=True).distinct()[:30]
    )
    return f"""Você é um assistente especializado no banco de dados de equipamentos de TI.

Contexto do banco de dados:
- Modelo: Equipamento (equipamentos de TI)
- Campos principais: numero_imobilizado (hostname), numero_serie, tipo, marca, modelo, local, setor, responsavel, empresa, status, sistema_operacional, versao_so, ip, mac_ethernet, mac_wifi, teamviewer_id, versao_office, observacoes
- Tipos disponíveis: {json.dumps(tipos, ensure_ascii=False)}
- Status disponíveis: {json.dumps(status, ensure_ascii=False)}
- Empresas cadastradas: {json.dumps(empresas, ensure_ascii=False)}
- Setores conhecidos: {json.dumps(setores, ensure_ascii=False)}

Regras:
1. Responda APENAS com dados que existem no banco. NÃO invente informações.
2. Se não souber responder, diga que não encontrou.
3. Use markdown simples: **negrito** para destaques, `codigo` para valores técnicos.
4. Seja direto e objetivo.
5. Para contagens, sempre mostre o número exato.
6. Quando listar equipamentos, inclua imobilizado, tipo, marca/modelo e status.
7. Responda em português."""


STOPWORDS = {
    'um', 'uma', 'o', 'a', 'os', 'as', 'de', 'da', 'do', 'das', 'dos',
    'em', 'no', 'na', 'nos', 'nas', 'para', 'por', 'com', 'sem',
    'quanto', 'quantos', 'quantas', 'como',
    'me', 'se', 'tem', 'temos', 'está', 'estão', 'todos', 'todas',
    'me mostre', 'liste', 'lista', 'exiba', 'exibe', 'fale',
    'sobre', 'todos', 'todas', 'temos',
}

TIPOS_SINONIMOS = {
    'desktop': 'DESKTOP', 'computador': 'DESKTOP', 'pc': 'DESKTOP',
    'notebook': 'NOTEBOOK', 'laptop': 'NOTEBOOK',
    'monitor': 'MONITOR', 'tela': 'MONITOR',
    'impressora': 'IMPRESSORA', 'impressoras': 'IMPRESSORA',
    'scanner': 'SCANNER',
    'nobreak': 'NOBREAK', 'no-break': 'NOBREAK', 'ups': 'NOBREAK',
    'switch': 'SWITCH',
    'roteador': 'ROTEADOR', 'router': 'ROTEADOR',
    'telefone': 'TELEFONE_IP', 'ramal': 'TELEFONE_IP',
    'projetor': 'PROJETOR', 'data show': 'PROJETOR',
    'tablet': 'TABLET',
    'outro': 'OUTRO',
}

STATUS_SINONIMOS = {
    'ativo': 'ATIVO', 'ativos': 'ATIVO', 'funcionando': 'ATIVO',
    'offline': 'OFFLINE', 'desligado': 'OFFLINE',
    'manutenção': 'EM_MANUTENCAO', 'manutencao': 'EM_MANUTENCAO', 'defeito': 'EM_MANUTENCAO', 'quebrado': 'EM_MANUTENCAO',
    'emprestado': 'EMPRESTADO', 'emprestados': 'EMPRESTADO',
    'estoque': 'ESTOQUE', 'reserva': 'ESTOQUE', 'guardado': 'ESTOQUE',
    'descartado': 'DESCARTADO', 'descartados': 'DESCARTADO', 'lixo': 'DESCARTADO',
}

MAPA_EMPRESAS_AD = {
    ('iveco', 'videira'): 'OU=USUÁRIOS,OU=VIDEIRA,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'chapeco'): 'OU=USUÁRIOS,OU=CHAPECO,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'concordia'): 'OU=USUÁRIOS,OU=CONCORDIA,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'itajai'): 'OU=USUÁRIOS,OU=ITAJAI,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'joinville'): 'OU=USUÁRIOS,OU=JOINVILLE,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'passo fundo'): 'OU=USUÁRIOS,OU=PASSO FUNDO,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'palhoca'): 'OU=USUÁRIOS,OU=PALHOÇA,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'rio do sul'): 'OU=USUÁRIOS,OU=RIO DO SUL,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'blumenau'): 'OU=USUÁRIOS,OU=BLUMENAU,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'sao jose dos pinhais'): 'OU=USUÁRIOS,OU=SÃO JOSÉ DOS PINHAIS,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'lages'): 'OU=USUÁRIOS,OU=LAGES,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'sao miguel do oeste'): 'OU=USUÁRIOS,OU=SÃO MIGUEL DO OESTE,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'canoinhas'): 'OU=USUÁRIOS,OU=CANOINHAS,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('iveco', 'guarapuava'): 'OU=USUÁRIOS,OU=GUARAPUAVA,OU=IVECO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('fiat', 'videira'): 'OU=USUÁRIOS,OU=VIDEIRA,OU=FIAT,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('fiat', 'campos novos'): 'OU=USUÁRIOS,OU=CAMPOS NOVOS,OU=FIAT,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('fiat', 'joacaba'): 'OU=USUÁRIOS,OU=JOAÇABA,OU=FIAT,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('fiat', 'capinzal'): 'OU=USUÁRIOS,OU=CAPINZAL,OU=FIAT,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('agropecuaria', 'imbuvial'): 'OU=USUÁRIOS,OU=IMBUIAL,OU=AGROPECUARIA,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('agropecuaria', 'taquara verde'): 'OU=USUÁRIOS,OU=TAQUARA VERDE,OU=AGROPECUARIA,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('agropecuaria', 'novo sao paulo'): 'OU=USUÁRIOS,OU=NOVO SÃO PAULO,OU=AGROPECUARIA,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('agropecuaria', 'silo e fabrica'): 'OU=USUÁRIOS,OU=SILO E FABRICA,OU=AGROPECUARIA,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('agropecuaria', 'iomere'): 'OU=USUÁRIOS,OU=IOMERE,OU=AGROPECUARIA,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('agropecuaria', 'quarto sitio'): 'OU=USUÁRIOS,OU=QUARTO SITIO,OU=AGROPECUARIA,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('agropecuaria', 'fraiburgo'): 'OU=USUÁRIOS,OU=FRAIBURGO,OU=AGROPECUARIA,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('rodoviario', 'videira'): 'OU=USUÁRIOS,OU=VIDEIRA,OU=RODOVIARIO MONTE SERENO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('rodoviario', 'vitoria'): 'OU=USUÁRIOS,OU=VITORIA DE SANTO ANTAO,OU=RODOVIARIO MONTE SERENO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('rodoviario', 'curitiba'): 'OU=USUÁRIOS,OU=CURITIBA,OU=RODOVIARIO MONTE SERENO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('rodoviario', 'barra velha'): 'OU=USUÁRIOS,OU=BARRA VELHA,OU=RODOVIARIO MONTE SERENO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('rodoviario', 'mossoro'): 'OU=USUÁRIOS,OU=MOSSORO,OU=RODOVIARIO MONTE SERENO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('rodoviario', 'sao paulo'): 'OU=USUÁRIOS,OU=SAO PAULO,OU=RODOVIARIO MONTE SERENO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('rodoviario', 'lontras'): 'OU=USUÁRIOS,OU=LONTRAS,OU=RODOVIARIO MONTE SERENO,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('seguradora', ''): 'OU=USUÁRIOS,OU=SEGURADORA,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
    ('administradores', ''): 'OU=USUÁRIOS,OU=ADMINISTRADORES,OU=GRUPO CARBONI,DC=grupocarboni,DC=local',
}


def extrair_termos(texto):
    texto = texto.lower().strip()
    texto = re.sub(r'[^\w\sáéíóúãõâêîôûàèìòùç]', ' ', texto)
    termos = texto.split()
    return [t for t in termos if t not in STOPWORDS and len(t) > 1]


def detectar_tipo(termos):
    for termo in termos:
        if termo in TIPOS_SINONIMOS:
            return TIPOS_SINONIMOS[termo]
    return None


def detectar_status(termos):
    for termo in termos:
        if termo in STATUS_SINONIMOS:
            return STATUS_SINONIMOS[termo]
    return None


def detectar_empresa(termos):
    empresas = Empresa.objects.all()
    texto = ' '.join(termos)
    for e in empresas:
        nome_clean = re.sub(r'[^\w\s]', '', e.nome.lower())
        if nome_clean in texto or e.nome.lower() in texto:
            return e
    return None


def detectar_setor(termos):
    texto = ' '.join(termos)
    setores = (
        Equipamento.objects.exclude(setor='')
        .values_list('setor', flat=True)
        .distinct()
    )
    match = []
    for s in setores:
        if s and len(s) > 2 and ' ' in texto and s.lower() in texto:
            match.append(s)
    if match:
        return max(match, key=len)
    return None


def detectar_intencao(texto, termos):
    texto_lower = texto.lower()

    if any(p in texto_lower for p in ['obrigado', 'valeu', 'brigado', 'thanks', 'vlw']):
        return 'agradecimento'

    if any(p in texto_lower for p in ['oi', 'ola', 'olá', 'hey', 'bom dia', 'boa tarde', 'boa noite']):
        return 'saudacao'

    if any(p in texto_lower for p in ['ajuda', 'help', 'comandos', 'o que sabe', 'o que você']):
        return 'ajuda'

    if any(p in texto_lower for p in ['manutenção', 'manutencao', 'manutenções', 'manutencoes']) and \
       any(p in texto_lower for p in ['aberta', 'abertas', 'aberto', 'pendente']):
        return 'manutencoes_abertas'

    if any(p in texto_lower for p in ['manutenção', 'manutencao', 'manutenções', 'manutencoes']):
        return 'listar_manutencoes'

    if any(p in texto_lower for p in ['inativo', 'inativos', 'desligado', 'desligados', 'offline']) and \
       any(p in texto_lower for p in ['quanto', 'quantos', 'dias', 'tempo', 'ha', 'ha quanto', 'antigas']):
        return 'offline_dias'
    if any(p in texto_lower for p in ['antigas', 'excluir do ad', 'ad nao', 'ad nao excluidas']):
        return 'offline_dias'

    if any(p in texto_lower for p in ['quanto', 'quantos', 'quantas', 'qauntos', 'qantos', 'total', 'conta', 'contagem']):
        return 'contagem'
    if 'quant' in texto_lower:
        return 'contagem'

    if any(p in texto_lower for p in ['detalhe', 'detalhes', 'info', 'informação', 'informacoes', 'sobre o', 'sobre a']):
        return 'detalhe'

    if any(p in texto_lower for p in ['qual o', 'qual a', 'qual é', 'qual e', 'quais', 'qual']) and \
       any(p in texto_lower for p in ['ip', 'serial', 'série', 'serie', 'mac', 'teamviewer', 'tv', 'marca', 'modelo', 'hostname', 'imobilizado', 'numero', 'número', 'patrimonio', 'patrimônio']):
        return 'campo_especifico'

    if any(p in texto_lower for p in ['busca', 'buscar', 'procure', 'encontre', 'acha', 'achar', 'localize']):
        return 'busca'

    if any(p in texto_lower for p in ['ping', 'pingar', 'respondendo', 'ativo mesmo', 'reachable', 'online mesmo']):
        return 'ping_test'
    if 'ping' in texto_lower:
        return 'ping_test'

    if any(p in texto_lower for p in ['criar usuário', 'criar usuario', 'novo usuário', 'novo usuario', 'novousuario', 'criarusuario']):
        return 'criar_usuario_ad'
    if re.match(r'criar\s+\w+\s+\w+\s+(?:na|no|da|do|em|para)\s+', texto_lower):
        return 'criar_usuario_ad'

    return 'listagem'


def classificar_intencao(texto):
    termos = extrair_termos(texto)
    intencao = detectar_intencao(texto, termos)
    tipo = detectar_tipo(termos)
    status = detectar_status(termos)
    empresa = detectar_empresa(termos)
    setor = detectar_setor(termos)

    return {
        'intencao': intencao,
        'termos': termos,
        'texto_original': texto,
        'tipo': tipo,
        'status': status,
        'empresa': empresa,
        'setor': setor,
    }


def executar_contagem(analise):
    qs = Equipamento.objects.all()
    filtros = []
    if analise['tipo']:
        qs = qs.filter(tipo=analise['tipo'])
        filtros.append(analise['tipo'])
    if analise['status']:
        qs = qs.filter(status=analise['status'])
        filtros.append(analise['status'])
    if analise['empresa']:
        qs = qs.filter(empresa=analise['empresa'])
        filtros.append(analise['empresa'].nome)
    if analise['setor']:
        qs = qs.filter(setor=analise['setor'])
        filtros.append(analise['setor'])

    total = qs.count()

    if filtros:
        msg = f"Tenho **{total}** equipamento(s)" + "".join(f" de {f}" for f in filtros)
    else:
        por_tipo = Equipamento.objects.values('tipo').annotate(total=Count('id')).order_by('-total')
        msg = f"Ao todo são **{total}** equipamentos cadastrados.\n\n"
        det = []
        for t in por_tipo:
            label = dict(Equipamento.TIPOS).get(t['tipo'], t['tipo'])
            det.append(f"- {label}: {t['total']}")
        msg += '\n'.join(det)

    return msg


def executar_listagem(analise):
    qs = Equipamento.objects.select_related('empresa').all()
    filtros_nome = []

    if analise['tipo']:
        qs = qs.filter(tipo=analise['tipo'])
        filtros_nome.append(dict(Equipamento.TIPOS).get(analise['tipo'], analise['tipo']))
    if analise['status']:
        qs = qs.filter(status=analise['status'])
        filtros_nome.append(dict(Equipamento.STATUS).get(analise['status'], analise['status']))
    if analise['empresa']:
        qs = qs.filter(empresa=analise['empresa'])
        filtros_nome.append(analise['empresa'].nome)
    if analise['setor']:
        qs = qs.filter(setor=analise['setor'])
        filtros_nome.append(analise['setor'])

    qs = qs.order_by('-criado_em')[:15]

    if not qs:
        return f"Nenhum equipamento encontrado{' de ' + ', '.join(filtros_nome) if filtros_nome else ''}."

    titulo = f"Equipamentos{' ' + ', '.join(filtros_nome) if filtros_nome else ''}"
    linhas = []
    for eq in qs:
        tv = f" | TV: {eq.teamviewer_id}" if eq.teamviewer_id else ""
        ip = f" | IP: {eq.ip}" if eq.ip else ""
        linhas.append(f"• **{eq.numero_imobilizado}** — {eq.marca} {eq.modelo} ({dict(Equipamento.TIPOS).get(eq.tipo, eq.tipo)}){ip}{tv}")

    if qs.count() >= 15:
        linhas.append(f"\n_Mostrando 15 de {qs.count()}+ resultados. Seja mais específico._")

    return f"**{titulo}** ({qs.count()} encontrados):\n\n" + '\n'.join(linhas)


def executar_ping(analise):
    import subprocess, json, time
    if analise['status']:
        qs = Equipamento.objects.filter(status=analise['status'])
    else:
        qs = Equipamento.objects.filter(status='ATIVO').exclude(ip__isnull=True).exclude(ip__exact='')
    total = qs.count()
    if total == 0:
        return "Nenhum equipamento com IP cadastrado para testar."

    amostra = list(qs.values('numero_imobilizado', 'ip')[:20])
    msg = f"Testando ping em **{len(amostra)}** de **{total}** equipamentos ativos com IP...\n\n"

    online = 0
    offline = 0
    for eq in amostra:
        hostname = eq['numero_imobilizado']
        ip = eq['ip']
        try:
            ping = subprocess.run(
                ['ping', '-n', '1', '-w', '2000', ip],
                capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW
            )
            if ping.returncode == 0:
                online += 1
                msg += f"[OK] **{hostname}** ({ip}) — respondeu\n"
            else:
                offline += 1
                msg += f"[FALHOU] **{hostname}** ({ip}) — sem resposta\n"
        except Exception:
            offline += 1
            msg += f"[ERRO] **{hostname}** ({ip}) — erro no teste\n"
        time.sleep(0.1)

    msg += f"\n**Resultado:** {online} respondendo, {offline} sem resposta (de {len(amostra)} testados)"
    if total > 20:
        msg += f"\n_Mais {total - 20} equipamentos não testados. Use 'ping todos' para testar todos (pode levar minutos)._"
    return msg


def executar_offline_dias(analise):
    from datetime import date
    qs = Equipamento.objects.filter(status='OFFLINE').order_by('atualizado_em')
    total = qs.count()
    if total == 0:
        return "Não há equipamentos com status OFFLINE."

    hoje = date.today()
    faixas = {'0-30 dias': 0, '31-90 dias': 0, '91-365 dias': 0, '+1 ano': 0, '+2 anos': 0}
    detalhes = []
    for eq in qs:
        if eq.atualizado_em:
            dias = (hoje - eq.atualizado_em.date()).days
        else:
            dias = (hoje - eq.criado_em.date()).days if eq.criado_em else 9999

        if dias <= 30:
            faixas['0-30 dias'] += 1
        elif dias <= 90:
            faixas['31-90 dias'] += 1
        elif dias <= 365:
            faixas['91-365 dias'] += 1
        elif dias <= 730:
            faixas['+1 ano'] += 1
        else:
            faixas['+2 anos'] += 1

        if dias > 365:
            detalhes.append(f"• **{eq.numero_imobilizado}** — {dias} dias ({eq.marca} {eq.modelo})")

    msg = f"**{total} equipamentos OFFLINE**\n\n"
    msg += "Distribuição por tempo:\n"
    for faixa, qtd in faixas.items():
        if qtd > 0:
            msg += f"• {faixa}: {qtd}\n"

    if detalhes:
        msg += f"\n**Há +1 ano sem atualização ({len(detalhes)}):**\n"
        for d in detalhes[:15]:
            msg += d + "\n"
        if len(detalhes) > 15:
            msg += f"_...e mais {len(detalhes) - 15}_"

    return msg


def executar_busca(analise):
    texto = analise['texto_original'].lower()
    termos_busca = [t for t in analise['termos'] if t not in STOPWORDS]

    padrao_imobilizado = re.search(
        r'(?:imobilizado|patrim[oô]nio|n[úu]mero|hostname|código|codigo|patrimonio)\s*[:\s]*([a-z0-9\-]+)',
        texto, re.IGNORECASE
    )
    padrao_serial = re.search(
        r'(?:serial|s[ée]rie|n[úu]mero de s[ée]rie|ns[:\s]*)([a-z0-9\-]+)',
        texto, re.IGNORECASE
    )
    padrao_ip = re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', texto)
    padrao_mac = re.search(r'\b([0-9a-f]{2}[-:][0-9a-f]{2}[-:][0-9a-f]{2}[-:][0-9a-f]{2}[-:][0-9a-f]{2}[-:][0-9a-f]{2})\b', texto, re.IGNORECASE)
    padrao_tv = re.search(r'\b(\d{9})\b', texto)

    qs = Equipamento.objects.select_related('empresa').all()

    if padrao_imobilizado:
        valor = padrao_imobilizado.group(1)
        qs = qs.filter(numero_imobilizado__icontains=valor)
    elif padrao_serial:
        valor = padrao_serial.group(1)
        qs = qs.filter(numero_serie__icontains=valor)
    elif padrao_ip:
        ip = padrao_ip.group(0)
        qs = qs.filter(ip__icontains=ip)
    elif padrao_mac:
        mac = padrao_mac.group(1)
        qs = qs.filter(Q(mac_ethernet__icontains=mac) | Q(mac_wifi__icontains=mac))
    elif padrao_tv and any(t in texto for t in ['teamviewer', 'tv']):
        tv = padrao_tv.group(1)
        qs = qs.filter(teamviewer_id=tv)
    else:
        termo_busca = ' '.join(termos_busca)
        if termo_busca:
            q_base = Q()
            for campo in ['numero_imobilizado', 'numero_serie', 'modelo', 'marca', 'observacoes']:
                q_base |= Q(**{f'{campo}__icontains': termo_busca})
            qs = qs.filter(q_base)

    qs = qs[:10]

    if not qs:
        return "Não encontrei nenhum equipamento com esses critérios."

    linhas = []
    for eq in qs:
        ip = f" | IP: {eq.ip}" if eq.ip else ""
        tv = f" | TV: {eq.teamviewer_id}" if eq.teamviewer_id else ""
        linhas.append(
            f"• **{eq.numero_imobilizado}** ({dict(Equipamento.TIPOS).get(eq.tipo, eq.tipo)})\n"
            f"  _{eq.marca} {eq.modelo}_ — {dict(Equipamento.STATUS).get(eq.status, eq.status)}{ip}{tv}"
        )

    return f"**Resultados da busca:**\n\n" + '\n\n'.join(linhas)


def executar_detalhe(analise):
    termos = analise['termos']
    texto = analise['texto_original']

    padrao = re.search(
        r'(?:sobre o|sobre a|detalhe[s]?\s*(?:do|da|de)?|info\s*(?:do|da|de)?)\s*[:\s]*([a-z0-9\-]+)',
        texto, re.IGNORECASE
    )

    if padrao:
        termo = padrao.group(1)
    elif termos:
        termo = termos[-1]
    else:
        return "Sobre qual equipamento você quer saber?"

    eq = (
        Equipamento.objects
        .select_related('empresa')
        .filter(Q(numero_imobilizado__icontains=termo) | Q(numero_serie__icontains=termo))
        .first()
    )
    if not eq:
        return f"Não encontrei equipamento com o termo '{termo}'."

    tv = f"TeamViewer: `{eq.teamviewer_id}`" if eq.teamviewer_id else ""
    ip = f"IP: `{eq.ip}`" if eq.ip else ""
    macs = ' | '.join(filter(None, [
        f"Ethernet: `{eq.mac_ethernet}`" if eq.mac_ethernet else "",
        f"Wi-Fi: `{eq.mac_wifi}`" if eq.mac_wifi else "",
    ]))
    so = f"SO: {eq.sistema_operacional} {eq.versao_so}".strip() if eq.sistema_operacional else ""
    office = f"Office: {eq.versao_office}" if eq.versao_office else ""

    linhas = [f"**{eq.numero_imobilizado}**"]
    linhas.append(f"Tipo: {dict(Equipamento.TIPOS).get(eq.tipo, eq.tipo)} | Status: **{dict(Equipamento.STATUS).get(eq.status, eq.status)}**")
    linhas.append(f"Marca/Modelo: {eq.marca} {eq.modelo}")
    linhas.append(f"Série: `{eq.numero_serie or '—'}`")
    if eq.empresa:
        linhas.append(f"Empresa: {eq.empresa.nome}")
    linhas.append(f"Setor: {eq.setor} | Local: {eq.local}")
    if eq.responsavel:
        linhas.append(f"Responsável: {eq.responsavel}")
    if ip:
        linhas.append(ip)
    if tv:
        linhas.append(tv)
    if macs:
        linhas.append(macs)
    if so:
        linhas.append(so)
    if office:
        linhas.append(office)
    if eq.observacoes:
        linhas.append(f"Obs: {eq.observacoes[:200]}")

    return '\n'.join(linhas)


def executar_manutencoes_abertas(analise):
    abertas = Manutencao.objects.filter(status__in=['ABERTA', 'EM_ANDAMENTO']).select_related('equipamento', 'tecnico')
    total = abertas.count()
    if total == 0:
        return "Não há manutenções abertas no momento."

    msg = f"**{total} manutenção(ões) aberta(s):**\n\n"
    for m in abertas[:10]:
        eq = m.equipamento
        tecnico = m.tecnico.get_full_name() or m.tecnico.username if m.tecnico else '—'
        msg += f"• {eq.numero_imobilizado} — {m.get_tipo_display()} | {m.get_status_display()} | Técnico: {tecnico}\n"

    return msg


def _sanitizar_ad(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ASCII", "ignore").decode("ASCII")
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9.]", "", texto)
    return texto


def _gerar_login_ad(nome, sobrenome):
    n = _sanitizar_ad(nome)
    s = _sanitizar_ad(sobrenome).replace(" ", "")
    login = f"{n}.{s}"[:20] if n and s else n[:20]
    return login


def _resolver_ou_ad(empresa_raw, filial_raw):
    empresa = empresa_raw.lower().strip()
    filial = filial_raw.lower().strip() if filial_raw else ""
    chaves = [(empresa, filial), (empresa, '')]
    for chave in chaves:
        if chave in MAPA_EMPRESAS_AD:
            return MAPA_EMPRESAS_AD[chave], None
    return None, f"Empresa '{empresa_raw}' ou filial '{filial_raw}' não reconhecida. Digite *ajuda* para ver as opções."


def _executar_criar_usuario_ad(texto):
    texto_lower = texto.lower().strip()

    m = re.match(
        r'(?:criar|nov[oa])\s+(?:usu[aá]ri[oa]\s+)?'
        r'(.+?)\s+'  # nome completo (non-greedy)
        r'(?:na|no|da|do|em|para|da\s+empresa)\s+'
        r'(\S+?)'  # empresa (uma palavra)
        r'(?:\s+(.+))?$',  # filial (restante, opcional)
        texto_lower
    )
    if not m:
        return (
            "Não entendi. Formato: *criar usuário Nome Sobrenome na EMPRESA filial*\n"
            "Exemplo: *criar usuário João Silva na iveco videira*\n"
            "Empresas disponíveis: iveco, fiat, agropecuaria, rodoviario, seguradora"
        )

    nome_completo = m.group(1).strip().title()
    empresa = m.group(2).strip().lower()
    filial = (m.group(3) or '').strip()

    partes = nome_completo.split(maxsplit=1)
    nome = partes[0]
    sobrenome = partes[1] if len(partes) > 1 else nome

    ou, erro = _resolver_ou_ad(empresa, filial)
    if erro:
        return erro

    login = _gerar_login_ad(nome, sobrenome)
    nome_display = f"{nome} {sobrenome}".strip()
    senha = settings.AD_DEFAULT_PASSWORD or "Altere@2026"

    ps_cmd = (
        f"New-ADUser "
        f"-Name '{nome_display}' "
        f"-GivenName '{nome}' "
        f"-Surname '{sobrenome}' "
        f"-SamAccountName '{login}' "
        f"-UserPrincipalName '{login}@grupocarboni.local' "
        f"-Path '{ou}' "
        f"-AccountPassword (ConvertTo-SecureString '{senha}' -AsPlainText -Force) "
        f"-Enabled $true -PassThru;"
        f"Set-ADUser -Identity '{login}' -ChangePasswordAtLogon $true"
    )

    try:
        r = subprocess.run(
            ['powershell', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if r.returncode == 0:
            return (
                f"> Usuário criado com sucesso!\n\n"
                f"**Nome:** {nome_display}\n"
                f"**Login:** `{login}`\n"
                f"**Senha:** `{senha}` (deverá trocar no 1º acesso)\n"
                f"**Local:** {empresa.upper()} / {filial.upper() if filial else '--'}"
            )
        else:
            erro_msg = r.stderr.strip()[:500]
            return f"> Erro ao criar usuário:\n```\n{erro_msg}\n```"
    except subprocess.TimeoutExpired:
        return "O comando excedeu o tempo limite. Tente novamente."
    except Exception as e:
        return f"> Erro inesperado: {e}"


def _gemini_pergunta(client, texto):
    total_equip = Equipamento.objects.count()
    por_tipo = list(Equipamento.objects.values('tipo').annotate(total=Count('id')).order_by('-total'))
    por_status = list(Equipamento.objects.values('status').annotate(total=Count('id')).order_by('-status'))
    manut_abertas = Manutencao.objects.filter(status__in=['ABERTA', 'EM_ANDAMENTO']).count()

    contexto = f"""
Dados atuais do banco:
- Total de equipamentos: {total_equip}
- Distribuição por tipo: {json.dumps(por_tipo, ensure_ascii=False)}
- Distribuição por status: {json.dumps(por_status, ensure_ascii=False)}
- Manutenções abertas: {manut_abertas}
"""

    prompt = f"""{_sistema_prompt()}

{contexto}

Pergunta do usuário: {texto}

Com base nos dados acima, responda a pergunta do usuário. Se precisar de dados mais específicos (como listar equipamentos), responda com o que você sabe do contexto e sugira filtros mais específicos.
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return None


def _mapear_campo(texto_lower):
    if 'ip' in texto_lower:
        return 'ip', 'IP'
    if any(p in texto_lower for p in ['serial', 'série', 'serie', 'numero de serie', 'numero de série']):
        return 'numero_serie', 'serial'
    if 'mac' in texto_lower:
        return None, 'MAC'
    if any(p in texto_lower for p in ['teamviewer', 'tv']):
        return 'teamviewer_id', 'TeamViewer'
    if 'marca' in texto_lower:
        return 'marca', 'marca'
    if 'modelo' in texto_lower:
        return 'modelo', 'modelo'
    if any(p in texto_lower for p in ['hostname', 'imobilizado', 'numero', 'número', 'patrimonio', 'patrimônio']):
        return 'numero_imobilizado', 'hostname'
    return None, None


def executar_campo_especifico(analise):
    texto = analise['texto_original'].lower()
    campo, campo_label = _mapear_campo(texto)
    if not campo:
        return executar_listagem(analise)

    termos = analise['termos']
    ignorar = {'ip', 'serial', 'série', 'serie', 'mac', 'teamviewer', 'tv', 'marca', 'modelo', 'hostname', 'imobilizado', 'numero', 'número', 'patrimonio', 'patrimônio', 'qual', 'quais', 'computador', 'notebook', 'desktop', 'pc', 'do', 'da', 'de', 'o', 'a', 'os', 'as'}
    nome_termos = [t for t in termos if t not in ignorar]
    if not nome_termos:
        return executar_listagem(analise)

    nome_busca = ' '.join(nome_termos)

    q_base = Q()
    for t in nome_termos:
        q_base &= Q(responsavel__icontains=t)
    if not nome_termos:
        q_base = Q(numero_imobilizado__icontains=nome_busca)

    qs = Equipamento.objects.filter(q_base)

    if not qs:
        qs = Equipamento.objects.filter(numero_imobilizado__icontains=nome_busca.replace(' ', '-'))

    if not qs:
        return f"Não encontrei equipamento para '{nome_busca}'."

    eq = qs.first()
    valor = getattr(eq, campo) or '—'
    return f"**{eq.numero_imobilizado}** — {campo_label}: `{valor}`"


def processar(texto):
    client = _get_gemini_client()
    if client:
        resposta = _gemini_pergunta(client, texto)
        if resposta:
            return resposta

    analise = classificar_intencao(texto)

    if analise['intencao'] == 'agradecimento':
        return "Por nada! Estou aqui para ajudar."
    if analise['intencao'] == 'saudacao':
        return "Ola! Como posso ajudar? Pergunte sobre equipamentos, manutencoes, ou digite *ajuda* para ver o que eu sei fazer."

    if analise['intencao'] == 'ajuda':
        return (
            "**O que eu sei fazer:**\n\n"
            "• *Quantos equipamentos temos?* — contagem geral\n"
            "• *Quantos desktops ativos?* — contagem com filtros\n"
            "• *Liste os notebooks* — lista por tipo\n"
            "• *Equipamentos em manutenção* — lista por status\n"
            "• *Busque pelo PC-FINANCEIRO01* — busca por imobilizado\n"
            "• *Detalhes do servidor XYZ* — informações completas\n"
            "• *Manutenções abertas* — lista de OS pendentes\n"
            "• *Equipamentos da empresa X* — filtra por empresa\n"
            "• *Procure pelo IP 192.168.* — busca por IP\n"
            "• *Qual o serial do PC-ADMIN?* — campo específico\n"
            "• *Ping nos ativos* — testa se equipamentos ATIVO respondem\n"
            "• *Inativos há quantos dias?* — mostra tempo offline das máquinas antigas\n"
            "• *Criar usuário João Silva na iveco videira* — cria usuário no AD (senha: Hoje#2026)"
        )

    if analise['intencao'] == 'contagem':
        return executar_contagem(analise)

    if analise['intencao'] == 'listagem':
        return executar_listagem(analise)

    if analise['intencao'] == 'busca':
        return executar_busca(analise)

    if analise['intencao'] == 'detalhe':
        return executar_detalhe(analise)

    if analise['intencao'] == 'campo_especifico':
        return executar_campo_especifico(analise)

    if analise['intencao'] == 'manutencoes_abertas':
        return executar_manutencoes_abertas(analise)

    if analise['intencao'] == 'ping_test':
        return executar_ping(analise)

    if analise['intencao'] == 'offline_dias':
        return executar_offline_dias(analise)

    if analise['intencao'] == 'criar_usuario_ad':
        return _executar_criar_usuario_ad(texto)

    return (
        "Não entendi sua pergunta. Tente:\n"
        "• *Quantos equipamentos?*\n"
        "• *Liste os desktops*\n"
        "• *Busque por PC-ADMIN*\n"
        "• *Detalhes do servidor X*\n"
        "• Digite *ajuda* para ver todas as opções"
    )
