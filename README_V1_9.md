# AIAffiliateIntelligence V1.9 — SaaS Foundation

Base: V1.8/V1.8.1 recebida.

## Implementado nesta versão

- Cadastro e login JWT (12h), senha com bcrypt.
- Empresa/workspace (tenant) e associação usuário × empresa.
- RBAC: OWNER, ADMIN, EDITOR, VIEWER.
- Trial de 14 dias e catálogo de planos TRIAL / STARTER / PRO / BUSINESS.
- Entitlements/limites armazenados como configuração do plano (não hardcoded no frontend).
- Estrutura de assinatura independente de provedor de pagamento.
- Auditoria básica de ações administrativas.
- Tela Equipe e permissões.
- Tela Plano e assinatura.
- Central de Automação de Conteúdo (Autopilot) com regras de score mínimo, limite diário, tom, público e duração.
- CORS inclui https://iaaffintel.com.
- Estrutura `company_id` adicionada às entidades sociais/conteúdo para transição multi-tenant.

## Importante — migração segura da V1.8

A V1.8 era single-tenant e usa `ADMIN_SETUP_KEY`. A V1.9 introduz autenticação SaaS sem remover imediatamente o fluxo legado, para evitar quebrar Mercado Livre/TikTok durante a revisão do app. O passo seguinte é migrar cada endpoint de negócio para `Bearer JWT + company_id` e atribuir os registros legados ao primeiro workspace do proprietário. Só depois deve-se retirar `ADMIN_SETUP_KEY` da interface.

## Monetização

A estrutura de planos e assinatura está pronta para receber um gateway, mas **checkout real não foi ativado**. Isso é intencional: primeiro fechamos tenant isolation e entitlements; depois conectamos o provedor de cobrança e webhooks.

## Central de conteúdo — direção V2

A automação foi modelada em pipeline:

`oportunidade -> briefing factual -> variantes por canal -> mídia -> revisão -> aprovação -> fila -> publicação -> métricas/aprendizado`

A geração atual da V1.8 continua determinística. A próxima etapa deve plugar um provedor de IA por interface de serviço, com grounding nos dados verificados do produto, versionamento de prompt, custo por geração, fila assíncrona, regeneração parcial e aprovação humana. Não publicar automaticamente apenas porque o conteúdo foi gerado.

## Novos endpoints

- `POST /api/v1/saas/auth/register`
- `POST /api/v1/saas/auth/login`
- `GET /api/v1/saas/me`
- `GET|POST /api/v1/saas/members`
- `PATCH /api/v1/saas/members/{id}`
- `GET /api/v1/saas/plans`
- `GET|PUT /api/v1/saas/automation-profile`
- `GET /api/v1/saas/audit`

## Novas páginas

- `/cadastro`
- `/login`
- `/equipe`
- `/plano`
- `/automacao`

## Deploy

Adicionar/confirmar em produção:

- `JWT_SECRET`: segredo aleatório forte, diferente de qualquer outra chave.
- Manter as variáveis V1.8 existentes.
- Não expor `JWT_SECRET`, tokens OAuth ou R2 no frontend.

Antes do deploy de produção, testar a migração em uma cópia do PostgreSQL.
