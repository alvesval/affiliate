# AIAffiliate Intelligence — Commercial RC4 Campaigns

## Central de Campanhas
- Renomeia Social Publishing para **Central de Campanhas**.
- Criação manual movida para modal, liberando a tela para gestão.
- Atalho separado para **Automatizar campanha**.
- Abas: Visão geral, Automatizadas, Manuais, Em andamento e Concluídas.
- Filtros por busca, status e canal.
- Cards operacionais com origem, status, canais, duração e progresso da jornada.
- KPIs de campanhas em andamento, aguardando aprovação e que precisam de atenção.
- Mantém a Jornada detalhada da campanha já validada visualmente.

## Origem auditável
- Novo campo `content_campaigns.origin` (`manual` / `automation`).
- Campanhas criadas pelo fluxo manual são gravadas como `manual`.
- Campanhas geradas por `/automation/prepare` são gravadas como `automation`.
- Migração idempotente recupera a origem de campanhas automatizadas antigas usando `content_automation_runs.detail_json`, quando disponível.

## API
- `GET /api/v1/social/campaigns` agora retorna `origin`, `platforms`, `progress`, `completed` e `needs_attention`.
- Detalhe/criação de campanha retornam `origin`.

## Validação
- Backend: `py_compile` executado com sucesso nos arquivos alterados.
- Frontend: verificação TypeScript direcionada não apontou erro em `conteudos/page.tsx` após instalação parcial das dependências.
- O build Next completo não pôde ser concluído neste ambiente: `npm ci` excedeu o tempo disponível e o binário `next` não chegou a ser instalado. Execute `npm ci && npm run build` no pipeline/local antes do deploy.
