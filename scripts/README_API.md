# Sincronização Automática de Ativos de Rede

## Visão Geral

Sistema de inventário automático que sincroniza computadores da rede Windows com o **Controle de Ativos**. Um script PowerShell coleta dados dos computadores via Active Directory + CIM/WMI e envia para a API Django, que cadastra ou atualiza os registros automaticamente.

---

## 1. Endpoint da API

```
POST /api/ativos/sync/
Content-Type: application/json
Authorization: Token SUA_CHAVE_AQUI
```

### Exemplo de payload

```json
[
  {
    "nome": "PC-FINANCEIRO01",
    "ip": "192.168.0.25",
    "usuario": "DOMINIO\\usuario",
    "fabricante": "Dell Inc.",
    "modelo": "OptiPlex 3090",
    "serial": "ABC1234",
    "processador": "Intel Core i5-10500",
    "memoria_gb": 8,
    "sistema": "Windows 11 Pro",
    "ultimo_logon": "2026-06-11T08:30:00-03:00",
    "status_rede": "online"
  }
]
```

### Campos aceitos

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `nome` | string | sim | Nome do computador (hostname) |
| `ip` | string | não | Endereço IPv4 |
| `usuario` | string | não | Último usuário logado |
| `fabricante` | string | não | Fabricante (Dell, HP, etc) |
| `modelo` | string | não | Modelo do equipamento |
| `serial` | string | não | Nº de série (chave primária para matching) |
| `processador` | string | não | Descrição da CPU |
| `memoria_gb` | int | não | Memória RAM em GB |
| `sistema` | string | não | Sistema operacional |
| `ultimo_logon` | string (ISO 8601) | não | Data/hora do último logon |
| `status_rede` | string | não | `online`, `offline` ou `desconhecido` |

### Resposta

```json
{
  "criados": 5,
  "atualizados": 20,
  "erros": []
}
```

### Regras de atualização

1. Se existir ativo com o mesmo **serial**, atualiza os dados.
2. Se não tiver serial, procura pelo **nome**.
3. Se não existir nenhum dos dois, cadastra novo.
4. Computadores offline são marcados com `status_rede: offline`.

---

## 2. Configuração do Token

### No servidor Django

1. Abra o arquivo `.env` na raiz do projeto.
2. Adicione ou edite a linha:

```
INVENTORY_TOKEN=SEU_TOKEN_AQUI
```

3. Reinicie o servidor Django para aplicar a mudança.

> **Segurança**: Em produção, use um token forte gerado com `python -c "import uuid; print(uuid.uuid4())"`.

---

## 3. Script PowerShell

O script `sync_ativos.ps1` fica na pasta `scripts/` do projeto.

### Parâmetros

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `ApiUrl` | `http://SEU_SERVER:8000/api/ativos/sync/` | URL do endpoint |
| `Token` | `SEU_TOKEN_AQUI` | Token de autenticação |
| `TimeoutSegundos` | `30` | Timeout da requisição HTTP |
| `LogPath` | `C:\Inventario\sync_ativos.log` | Caminho do arquivo de log |

### Execução manual

```powershell
# Execução básica (servidor local)
.\scripts\sync_ativos.ps1

# Especificando servidor e token
.\scripts\sync_ativos.ps1 -ApiUrl "http://meuservidor:8000/api/ativos/sync/" -Token "meu-token-aqui"

# Apenas 10 segundos de timeout
.\scripts\sync_ativos.ps1 -TimeoutSegundos 10
```

---

## 4. Agendamento no Windows Task Scheduler

1. Abra o **Agendador de Tarefas** (`taskschd.msc`).
2. Clique em **Criar Tarefa...**.
3. **Geral**:
   - Nome: `Inventario Ativos - Sincronizacao`
   - Marcar "Executar com privilégios mais altos"
   - "Executar quer o usuário esteja logado ou não"
4. **Gatilhos**:
   - Novo → Diariamente às 22:00 (ou conforme necessidade)
   - Opcional: repetir a cada 1 hora por 24 horas
5. **Ações**:
   - Novo → Iniciar um programa
   - Programa: `powershell.exe`
   - Argumentos:
     ```
     -ExecutionPolicy Bypass -File "C:\caminho\para\scripts\sync_ativos.ps1" -ApiUrl "http://SEU_SERVIDOR:8000/api/ativos/sync/" -Token "SEU_TOKEN"
     ```
6. Ok → informar credenciais de uma conta com permissão de domínio.

---

## 5. Permissões Necessárias

### Para consulta AD (Active Directory)

- A conta que executa o script precisa de acesso de **leitura** ao AD.
- Usuário do domínio comum com permissão de "Domain Users" já consegue listar computadores.

### Para consulta CIM/WMI remota

- A conta precisa ser **administrador local** nos computadores alvo (típico para contas de suporte/domínio).
- Firewall liberado para:
  - **DCOM** (porta 135)
  - **WinRM** (porta 5985/5986 HTTP/HTTPS)
- Ou, alternativamente, habilitar o **Windows Remote Management (WinRM)**:

```powershell
# Em cada computador alvo (ou via GPO)
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*"
```

### Requisitos do servidor onde o script roda

- PowerShell 5.1 ou superior
- Módulo **ActiveDirectory** (parte do RSAT Tools)
  - Instalar: `Add-WindowsCapability -Name Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0 -Online`

---

## 6. Modelo de Dados (Django)

O model `Ativo` armazena:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `nome` | CharField | Nome do computador |
| `ip` | GenericIPAddressField | Endereço IP |
| `usuario` | CharField | Último usuário logado |
| `fabricante` | CharField | Fabricante |
| `modelo` | CharField | Modelo |
| `serial` | CharField (unique) | Nº de série |
| `processador` | CharField | CPU |
| `memoria_gb` | IntegerField | RAM em GB |
| `sistema_operacional` | CharField | SO |
| `ultimo_logon` | DateTimeField | Último logon |
| `status_rede` | CharField | Online / Offline |
| `origem` | CharField | "inventario_automatico" |
| `data_ultima_sincronizacao` | DateTimeField | Auto-atualizado |
| `criado_em` | DateTimeField | Auto-preenchido |

O registro pode ser visualizado e gerenciado no **admin Django** (`/admin/core/ativo/`).

---

## 7. Exemplo de Payload Completo

```json
[
  {
    "nome": "PC-ADM01",
    "ip": "192.168.1.10",
    "usuario": "DOMINIO\\joao.silva",
    "fabricante": "Dell Inc.",
    "modelo": "OptiPlex 7080",
    "serial": "ABC1234",
    "processador": "Intel Core i7-10700",
    "memoria_gb": 16,
    "sistema": "Windows 10 Pro",
    "ultimo_logon": "2026-06-11T14:30:00-03:00",
    "status_rede": "online"
  },
  {
    "nome": "PC-FINANCEIRO",
    "ip": "192.168.1.25",
    "usuario": "DOMINIO\\maria.oliveira",
    "fabricante": "HP Inc.",
    "modelo": "HP EliteDesk 800 G6",
    "serial": "XYZ5678",
    "processador": "Intel Core i5-10500",
    "memoria_gb": 8,
    "sistema": "Windows 11 Pro",
    "ultimo_logon": "2026-06-10T17:45:00-03:00",
    "status_rede": "online"
  },
  {
    "nome": "PC-ESTOQUE",
    "ip": null,
    "usuario": "",
    "fabricante": "",
    "modelo": "",
    "serial": "",
    "processador": "",
    "memoria_gb": null,
    "sistema": "",
    "ultimo_logon": null,
    "status_rede": "offline"
  }
]
```

> **Nota**: Quando `serial` é vazio ou nulo, o sistema usa o campo `nome` para buscar correspondência.
> Computadores offline são enviados com `status_rede: offline` e os demais campos vazios.
