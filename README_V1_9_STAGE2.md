# AIAffiliateIntelligence V1.9.1 — Tenant Isolation

Segunda etapa da SaaS Foundation.

## Alterações
- `ADMIN_SETUP_KEY` removida do fluxo de usuário e do frontend.
- JWT obrigatório para Catálogo, Dashboard, Conteúdo, Mercado Livre e Social.
- RBAC: leitura para usuário autenticado; escrita de conteúdo/produto para `EDITOR+`; integrações para `ADMIN+`.
- Produtos, preços, scores, conteúdo, campanhas, variantes, publicações, conexões sociais e OAuth do Mercado Livre isolados por `company_id`.
- OAuth state carrega o `company_id` no backend; callback não depende de sessão do navegador para descobrir o tenant.
- TikTok e Mercado Livre passam a ter conexão separada por empresa.
- Guard de autenticação no workspace; sessão inválida redireciona para `/login`.
- Frontend não solicita nem envia `X-Admin-Key`.

## Migração dos dados existentes da V1.8
Os registros antigos recebem `company_id = NULL` e ficam invisíveis para tenants por segurança. Depois de criar/logar com a empresa proprietária original, execute uma única vez:

`POST /api/v1/saas/legacy/claim`

com o JWT do `OWNER`. O endpoint só assume registros ainda sem empresa e grava auditoria. Não o execute para empresas novas.

## Deploy
1. Faça backup do PostgreSQL antes do primeiro deploy.
2. Suba o backend; as migrações idempotentes adicionam `company_id` e índices por tenant.
3. Crie/login no OWNER da empresa original.
4. Execute `/api/v1/saas/legacy/claim` uma vez para preservar os dados da V1.8.
5. Valide Catálogo, Estúdio, Mercado Livre e TikTok.
6. Só depois libere novos cadastros de clientes.

## Segurança
O isolamento é aplicado no backend. IDs recebidos na URL são sempre consultados junto com `company_id`; o frontend não é a barreira de segurança.

## Validação realizada
- `python -m compileall backend/app`: OK.
- Busca estática: não restam `X-Admin-Key`, `ADMIN_SETUP_KEY` ou `require_admin` no código executável do frontend/backend.
- Build Next.js não foi concluído neste ambiente porque a instalação de `node_modules` excedeu o tempo e deixou `next` indisponível. Execute `npm ci && npm run build` no CI/GitHub antes do deploy.
