# AIAffiliateIntelligence V1.10 — Commercial Foundation

Esta versão fecha a base dos quatro blocos anteriores ao lançamento em volume:

1. **Onboarding guiado**: checklist automático no dashboard até a primeira publicação.
2. **Cobrança e planos**: Checkout/Customer Portal via Stripe, webhook e consumo mensal. Requer variáveis STRIPE_*; nenhum segredo vai para o frontend.
3. **Growth Analytics**: coletor first-party de UTM/referrer, funil, trials, ativações, assinaturas, MRR, cancelamentos e indicações. A tela Crescimento é administrativa e requer `PLATFORM_ADMIN_EMAILS`.
4. **Automação do Estúdio**: execuções auditáveis, lote por oportunidade, consumo e campanhas em rascunho com aprovação humana separada da publicação.

## Variáveis novas
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- STRIPE_PRICE_STARTER
- STRIPE_PRICE_PRO
- STRIPE_PRICE_BUSINESS
- PLATFORM_ADMIN_EMAILS (lista separada por vírgula)

## Observações de produção
- Configure no provedor de cobrança os Price IDs dos planos antes de habilitar checkout.
- Configure o webhook para `/api/v1/billing/webhook`.
- O cálculo de MRR do painel usa o preço cadastrado em `plans`; conciliação financeira oficial deve vir do provedor de cobrança.
- O coletor Growth não aceita `company_id`/`user_id` do browser público.
- A publicação automática continua desacoplada da geração de conteúdo.
