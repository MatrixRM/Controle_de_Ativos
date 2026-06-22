# Controle de Ativos de TI

Sistema web para gerenciamento de equipamentos de informática, manutenções e estoque de peças e acessórios.

## Requisitos

- Python 3.11+
- Django 5.2.15
- python-decouple 3.8

## Instalação

1. Clone o repositório:

```bash
git clone <url-do-repositorio>
cd Controle_de_Ativos
```

2. Crie e ative um ambiente virtual:

```bash
python -m venv env
# Windows
env\Scripts\activate
# Linux/macOS
source env/bin/activate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Configure o arquivo `.env`:

Copie o arquivo de exemplo e ajuste as configurações:

```bash
cp .env.example .env
```

Edite o `.env` com suas configurações:

```ini
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
INVENTORY_TOKEN=seu-token-aqui
```

5. Execute as migrações:

```bash
python manage.py migrate
```

6. Popule dados iniciais (opcional):

```bash
python manage.py seed_empresas
python manage.py criar_tecnicos
```

7. Crie um superusuário:

```bash
python manage.py createsuperuser
```

8. Execute o servidor:

```bash
python manage.py runserver 8000
```

## Funcionalidades

### Equipamentos
- Cadastro completo com número de imobilizado, tipo, marca, modelo, etc.
- Filtros por tipo, status, empresa e busca textual
- Histórico de manutenções por equipamento
- Sincronização automática via inventário de rede (Active Directory + CIM/WMI)

### Manutenções
- Registro de ordens de serviço (corretiva, preventiva, upgrade)
- Acompanhamento por status (aberta, em andamento, concluída)
- Vínculo com técnico responsável e custos
- Geração automática de preventivas baseada na periodicidade do equipamento

### Estoque
- Controle de peças e acessórios com quantidade mínima
- Alertas automáticos para itens abaixo do mínimo
- Movimentações de entrada, saída, transferência e ajuste
- Atualização automática do saldo

### Notificações
- Alertas de estoque baixo
- Garantia próxima do vencimento
- Manutenções atrasadas
- Central de notificações com marcação de leitura

### Relatórios
- Relatório de equipamentos com gráficos por status, tipo e empresa
- Relatório de estoque com resumo por categoria
- Exportação para CSV

### Auditoria
- Log detalhado de todas as alterações nos registros
- Filtros por tabela e busca textual

### Assistente IA
- Chatbot integrado com Google Gemini
- Consulta de equipamentos, manutenções e estoque em linguagem natural

### Sincronização de Rede
- Coleta automática de inventário via Active Directory
- Descoberta de IP, MAC, TeamViewer, sistema operacional e Office via CIM/WMI
- Duas modalidades de sincronização: rápida (online) e completa

### Controle de Acesso
- Dois perfis: Administrador (acesso total) e Técnico (manutenções)
- Autenticação via Django Auth
- Views protegidas por login

## Perfis de Usuário

- **Administrador**: CRUD completo de equipamentos, empresas, estoque e manutenções
- **Técnico**: Visualização de equipamentos e registro de manutenções

## Scripts PowerShell

| Script | Descrição |
|--------|-----------|
| `sync_ativos.ps1` | Coleta inventário do AD e envia para API (com suporte a modo rápido) |
| `rotina_diaria.ps1` | Executa notificações, preventivas e atualização de rede |
| `backup_db.ps1` | Backup automático do banco SQLite |
| `registrar_tarefa.ps1` | Registra tarefas no Windows Task Scheduler |

## Tarefas Agendadas (Windows)

| Tarefa | Horário | Descrição |
|--------|---------|-----------|
| Inventario Ativos - Rapido | A cada 1h (08h-18h) | Sincronização rápida de máquinas online |
| Inventario Ativos - Completo | Diário 22:00 | Sincronização completa de todos os ativos |
| Rotina Diária | Diário 06:00 | Notificações, preventivas e info de rede |

## Tecnologias

- Django 5.2
- SQLite
- Google Gemini API
- PowerShell (scripts de automação)
- Docker (imagem disponível)
