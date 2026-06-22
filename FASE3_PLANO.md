# Fase 3 — Plano de Aprimoramentos e Infra/Deploy

---

## Bloco A — Aprimoramentos

### A1 — Manutenções Preventivas
**Objetivo:** Agendamento automático de manutenções preventivas com base em tempo ou uso.

- [ ] Adicionar campos `periodicidade_dias` (Integer) e `proxima_manutencao` (Date) no modelo `Equipamento`
- [ ] Ao criar equipamento, calcular `proxima_manutencao` baseado em `data_aquisicao + periodicidade_dias`
- [ ] Comando `manage.py verificar_preventivas`:
  - Lista equipamentos com `proxima_manutencao <= hoje`
  - Cria automaticamente `Manutencao(tipo='PREVENTIVA', ...)` para cada um
  - Atualiza `proxima_manutencao` para a próxima data
- [ ] Dashboard: card "Manutenções Preventivas Pendentes" com contagem e link
- [ ] Botão "Agendar Preventiva" no detail do equipamento

### A2 — Notificações
**Objetivo:** Alertas automáticos por email (ou outra integração) para eventos críticos.

- [ ] Configurar `EMAIL_*` no `.env` (servidor SMTP)
- [ ] Criar `core/notifications.py` com funções:
  - `notificar_estoque_baixo()` — dispara quando item fica abaixo do mínimo
  - `notificar_garantia_proxima()` — equipamentos com garantia vencendo em 30 dias
  - `notificar_preventivas_pendentes()` — manutenções preventivas atrasadas
- [ ] Comando `manage.py enviar_notificacoes` que roda todas as rotinas
- [ ] Histórico de notificações no banco (modelo `Notificacao`)
- [ ] **Opcional:** Webhook Teams/Slack para alertas críticos

### A3 — Auditoria (Log de Alterações)
**Objetivo:** Rastrear quem editou o quê e quando em equipamentos.

- [ ] Instalar `django-simple-history` ou implementar via signals
- [ ] Habilitar histórico no modelo `Equipamento` (e opcionalmente `ItemEstoque`)
- [ ] Exibir "Últimas alterações" no detail do equipamento:
  - Usuário, data, campo alterado, valor anterior → novo
- [ ] Página `/auditoria/` com busca por equipamento, usuário, período
- [ ] Exportar log de auditoria em CSV

### A4 — Importação em Lote (Excel/CSV)
**Objetivo:** Importar múltiplos equipamentos de uma planilha.

- [ ] Criar comando `manage.py importar_planilha --arquivo equipamentos.xlsx`
- [ ] Suporte a `.xlsx` (openpyxl) e `.csv`
- [ ] Mapeamento de colunas (ex: "Nº Imobilizado" → `numero_imobilizado`)
- [ ] Validação: relatório de erros com linhas rejeitadas
- [ ] Interface web: upload do arquivo + preview + confirmação

### A5 — API REST
**Objetivo:** Expor dados para integração com outros sistemas.

- [ ] Instalar `djangorestframework`
- [ ] Serializers para `Equipamento`, `Empresa`, `ItemEstoque`
- [ ] ViewSets com filtros, paginação, ordenação
- [ ] Autenticação via Token (já temos `INVENTORY_TOKEN`)
- [ ] Rotas:
  - `GET /api/v1/equipamentos/`
  - `GET /api/v1/equipamentos/{pk}/`
  - `GET /api/v1/empresas/`
  - `GET /api/v1/estoque/`
- [ ] Documentação automática (drf-spectacular ou swagger)

---

## Bloco B — Infra / Deploy

### B1 — Docker
**Objetivo:** Containerizar a aplicação para deploy consistente.

- [ ] `Dockerfile` baseado em `python:3.12-slim`
  - Instala dependências do sistema (pyodbc, etc.)
  - Copia requirements e instala
  - Copia projeto
  - Expõe porta 8000
  - CMD: `gunicorn ativos.wsgi:application`
- [ ] `docker-compose.yml` com:
  - `web`: serviço Django + Gunicorn
  - `db`: SQLite (volume persistente) ou PostgreSQL opcional
- [ ] `.dockerignore` (excluir `env/`, `.git/`, `__pycache__/`)
- [ ] Script `docker-build.ps1` para build local

### B2 — Deploy IIS (Windows Server)
**Objetivo:** Publicar no IIS da empresa (servidor Windows).

- [ ] Instalar e configurar `wfastcgi` no servidor
- [ ] `web.config` para IIS apontando para o virtualenv Python
- [ ] Script `deploy.ps1`:
  ```powershell
  git pull
  .\env\Scripts\python -m pip install -r requirements.txt
  .\env\Scripts\python manage.py migrate
  .\env\Scripts\python manage.py collectstatic --noinput
  iisreset
  ```
- [ ] Configurar `STATIC_ROOT` e `MEDIA_ROOT` no IIS
- [ ] Checklist de produção:
  - [ ] `DEBUG=False`
  - [ ] `SECRET_KEY` forte e segura
  - [ ] `ALLOWED_HOSTS` com IP do servidor
  - [ ] SSL/HTTPS configurado
  - [ ] Backup automático do `db.sqlite3`

### B3 — Scripts de Automação
**Objetivo:** Rotinas de manutenção agendadas no Windows (Task Scheduler).

- [ ] `scripts/backup_db.ps1` — copia `db.sqlite3` para pasta de backup com data
- [ ] `scripts/rotina_diaria.ps1` — roda todos os comandos:
  ```powershell
  python manage.py verificar_preventivas
  python manage.py enviar_notificacoes
  python manage.py atualizar_info_rede --ad-sync
  ```
- [ ] Tarefa agendada "Rotina Diária" rodando o script acima
- [ ] Tarefa agendada "Backup Semanal" rodando o backup

---

## Prioridade Sugerida

| Prioridade | Item | Esforço | Impacto |
|-----------|------|---------|---------|
| 1 | B2 — Deploy IIS | Médio | Crítico (produção) |
| 2 | A3 — Auditoria | Baixo | Alto (controle) |
| 3 | A2 — Notificações | Médio | Alto (proatividade) |
| 4 | A1 — Preventivas | Médio | Médio |
| 5 | B3 — Automação | Baixo | Médio |
| 6 | A4 — Importação | Médio | Médio |
| 7 | B1 — Docker | Alto | Médio |
| 8 | A5 — API REST | Alto | Baixo (futuro) |

---

*Documento gerado em 18/06/2026*
