# V1.12 — Vídeo IA + Monetização Stripe

## Correção do `TypeError: Failed to fetch`
- `NEXT_PUBLIC_API_URL` precisa apontar para a URL pública HTTPS do backend em produção. `localhost:8000` só funciona quando o navegador e o backend estão na mesma máquina.
- CORS agora inclui localhost, domínio principal, `www` e origens extras em `CORS_ORIGINS`.
- O frontend informa a URL da API e a origem do navegador quando a conexão falha.
- As configurações `OPENAI_API_KEY`, `OPENAI_TEXT_MODEL` e `OPENAI_VIDEO_MODEL` agora fazem parte de `Settings`; antes eram ignoradas pelo Pydantic Settings.

## Vídeo IA
Configure no backend:
```
OPENAI_API_KEY=...
OPENAI_TEXT_MODEL=gpt-5.6-luna
OPENAI_VIDEO_MODEL=sora-2
```
O plano controla `ai_video_month`. O consumo é registrado em `usage_counters.ai_video_generations`.

## Stripe — homologação
1. No Stripe, crie um produto/preço recorrente mensal para cada plano.
2. Copie os **Price IDs** (`price_...`), nunca os Product IDs (`prod_...`).
3. Configure no backend:
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_ENTRY=price_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_BUSINESS=price_...
FRONTEND_URL=https://seu-frontend
```
4. Crie um webhook Stripe apontando para:
```
https://SEU_BACKEND/api/v1/billing/webhook
```
5. Assine pelo menos estes eventos: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`.
6. Copie o Signing secret (`whsec_...`) para `STRIPE_WEBHOOK_SECRET`.
7. Teste tudo em modo Test antes de trocar para as chaves live.

A liberação do plano é confirmada pelo webhook, não pela página de sucesso do navegador.
