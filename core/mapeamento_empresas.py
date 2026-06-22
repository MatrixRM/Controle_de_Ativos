from .models import Empresa


def _empresa_por_segmento(sigla):
    cache = {}
    for e in Empresa.objects.all():
        cache[e.segmento] = e
    return cache.get(sigla)


PREFIXO_PARA_EMPRESA = {}

# IVECO (Carboni Distribuidora de Veículos LTDA) - ID 1
# Todas as filiais IVECO pertencem a Carboni Distribuidora
_PREFIXOS_IVECO = [
    'IVDA',  # IVECO Indaial
    'IITJ',  # IVECO Itajaí
    'ICHP',  # IVECO Chapecó
    'IJLE',  # IVECO Joinville
    'ICDA',  # IVECO Concórdia
    'IPFU',  # IVECO Passo Fundo
    'IRSU',  # IVECO Rio Sul
    'IPLH',  # IVECO Palhoça
    'IBLU',  # IVECO Blumenau
    'ILGS',  # IVECO Lages
    'ISJP',  # IVECO São José dos Pinhais
    'IGPV',  # IVECO Guarapuava
    'ICAN',  # IVECO ? 
    'ISMO',  # IVECO ?
    'ISDP',  # IVECO ?
    'ICBA',  # IVECO ?
    'ITJ',   # IVECO Itajaí (abreviado)
    'IRCTV', # IVECO ?
    'ICD',   # IVECO Concórdia (abreviado)
]

for p in _PREFIXOS_IVECO:
    PREFIXO_PARA_EMPRESA[p] = ('IVECO', 1)

# FIAT (Carboni Veículos LTDA) - ID 10
_PREFIXOS_FIAT = [
    'FVDA',  # Fiat Videira
    'FJBA',  # Fiat Joaçaba
    'FCNV',  # Fiat Campos Novos
    'FCPZ',  # Fiat Capinzal
    'FFBO',  # Fiat Fraiburgo
]

for p in _PREFIXOS_FIAT:
    PREFIXO_PARA_EMPRESA[p] = ('FIAT', 10)

# AGROPECUÁRIA (Agropecuária Carboni LTDA) - ID 3
_PREFIXOS_AGRO = [
    'AGRO',   # Agropecuária Carboni
    'ASIL',   # Almoxarifado Sil? (mesmo local da AFAB - Agropecuária)
    'ATQV',   # AGRO TQV
    'AFAB',   # Almoxarifado Fábrica (Agro)
    'AFBO',   # AGRO FBO
    'AIMB',   # AGRO ?
    'AIOM',   # AGRO ?
    'ANSP',   # AGRO ?
]

for p in _PREFIXOS_AGRO:
    PREFIXO_PARA_EMPRESA[p] = ('AGROP.', 3)

# RODOVIÁRIO (Rodoviário Monte Sereno LTDA) - ID 4
_PREFIXOS_ROD = [
    'RVDA',  # Rodoviário Monte Sereno
    'RVSA',  # Rodoviário ?
    'RMSS',  # Rodoviário Monte Sereno
    'RBVL',  # Rodoviário ?
    'RCTB',  # Rodoviário ?
    'RSPL',  # Rodoviário ?
    'RLTS',  # Rodoviário ?
    'RITJ',  # Rodoviário ?
    'RFBO',  # Rodoviário ?
    'RMS',   # Rodoviário ?
]

for p in _PREFIXOS_ROD:
    PREFIXO_PARA_EMPRESA[p] = ('ROD.', 4)

# VERDE VALE (Verde Vale Transporte) - ID 5
PREFIXO_PARA_EMPRESA['SVDA'] = ('V. VALE', 5)

# SERVIDORES - sem empresa
_PREFIXOS_SRV = ['SRV', 'DESKTOP', 'PC', 'TESTE', 'SERVIDOR', 'RESERVA',
                 'JULIANO', 'ANALYZER', 'ADMINISTRADOR1', 'ADMINISTRADOR2',
                 'C164CP01']

for p in _PREFIXOS_SRV:
    PREFIXO_PARA_EMPRESA[p] = (None, None)

# CARBONI (matriz)
PREFIXO_PARA_EMPRESA['CARBONI'] = ('IVECO', 1)
PREFIXO_PARA_EMPRESA['CARBONIDC1'] = ('IVECO', 1)

# CASE (Carboni Máquinas Agrícolas) - ID 9
PREFIXO_PARA_EMPRESA['CASE'] = ('CASE', 9)


def detectar_empresa_por_hostname(hostname):
    if not hostname:
        return None
    hostname = hostname.strip().upper()
    prefixo = hostname.split('-')[0] if '-' in hostname else hostname
    resultado = PREFIXO_PARA_EMPRESA.get(prefixo)
    if resultado:
        _, empresa_id = resultado
        return empresa_id
    # Tenta match parcial (ex: CARBONI em CARBONIVEEAM)
    for prefixo_possivel, (_, empresa_id) in PREFIXO_PARA_EMPRESA.items():
        if hostname.startswith(prefixo_possivel):
            return empresa_id
    return None
