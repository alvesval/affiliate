# AIAffiliateIntelligence v1.15 RC1 — Fechamento do ciclo comercial

## Entrega principal
- Pinterest OAuth Authorization Code por empresa, com state anti-CSRF e tokens criptografados.
- Scopes mínimos: boards:read, boards:write, pins:read, pins:write.
- Listagem de boards para seleção no fluxo de publicação.
- Video Pin real: registrar mídia -> upload MP4 -> polling de processamento -> Create Pin.
- Link de afiliado enviado no campo link do Pin.
- Capa usa prioritariamente referência visual real do produto; fallback para image_url oficial do produto.
- Metadados Pinterest persistidos em Publication para auditoria.
- SocialPublisher permanece extensível para TikTok, Pinterest e próximos canais.
- Stripe já suporta Checkout de assinatura, portal, webhook, falha de pagamento, cancelamento e mapeamento por Price ID. Para venda real, trocar SOMENTE por credenciais/Prices/Webhook do modo Live no ambiente de produção.

## Pinterest: requisito operacional
Apps novos precisam solicitar Trial access. Para produção com clientes, solicitar Standard access. Video Pins não são suportados pelo Sandbox; valide OAuth/boards em Trial e faça o vídeo real quando o acesso aplicável estiver aprovado.

## Variáveis novas/confirmadas
PINTEREST_CLIENT_ID
PINTEREST_CLIENT_SECRET
PINTEREST_REDIRECT_URI=https://SEU_BACKEND/api/v1/social/pinterest/callback

## Stripe Live checklist
1. Criar/confirmar Products e Prices no modo Live.
2. Configurar STRIPE_SECRET_KEY=sk_live_...
3. Configurar STRIPE_PRICE_ENTRY/STARTER/PRO/BUSINESS com price_... LIVE.
4. Criar webhook LIVE apontando para /billing/webhook/stripe e configurar o whsec_ correspondente.
5. Validar checkout, invoice.paid, payment_failed, portal, cancelamento e atualização do workspace.
6. Não copiar chaves para Git/ZIP.

## RC2 — Production Readiness

- Limites comerciais centralizados e aplicados a campanhas, publicações e gerações de texto por IA.
- Recursos pagos exigem assinatura ativa (`active`/`trialing`), evitando consumo antes da confirmação do Stripe.
- Contadores mensais passam a ser consumidos no fluxo principal de campanhas/publicações.
- Onboarding inclui ativação de cobrança e aceita qualquer rede social conectada como etapa social concluída.
- Pinterest expõe estado comercial `pending_trial | trial | standard` separadamente das credenciais OAuth, permitindo UX correta enquanto a aprovação externa está pendente.
- Versão da API atualizada para `1.15.0-rc2`.
