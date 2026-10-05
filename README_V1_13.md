# AIAffiliateIntelligence V1.13 — Pricing & Billing profissional

## Catálogo comercial atualizado
- Entrada: R$ 49/mês
- Starter: R$ 79/mês
- Pro: R$ 199/mês
- Business: R$ 299/mês

## Administração de preços
Nova tela `/precos` para administradores da plataforma (definidos em `PLATFORM_ADMIN_EMAILS`).
Ao alterar um valor, o backend cria um novo Price mensal no Stripe, salva o `price_...` no banco e passa a usá-lo automaticamente nos novos Checkouts. Não é necessário redeploy para futuras alterações de preço.

Assinaturas existentes permanecem no Price contratado; a aplicação não reajusta clientes silenciosamente.

## Webhook
A V1.13 aceita os dois caminhos:
- `/api/v1/billing/webhook`
- `/billing/webhook/stripe`

Isso mantém compatibilidade com o destino já criado no Stripe.

## Segurança
Nunca exponha `STRIPE_SECRET_KEY` ou `STRIPE_WEBHOOK_SECRET` no frontend. A criação de Price ocorre exclusivamente no backend e a tela de preços exige administrador da plataforma.
