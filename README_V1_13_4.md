# V1.13.4 — Password recovery e-mail observability

- Mantém a resposta pública genérica do `forgot-password` para impedir enumeração de contas.
- Registra no Railway quando o envio via Resend começa, é aceito ou falha.
- Em erro HTTP do Resend, registra status e corpo da resposta (sem expor a API key).
- Mascara o endereço do destinatário nos logs.
- Registra o `resend_id` quando o Resend aceita o e-mail.
- Mantém a invalidação do token de redefinição quando o envio falha.

Variáveis esperadas no backend:
- `RESEND_API_KEY`
- `EMAIL_FROM=AIAffiliateIntelligence <noreply@iaaffintel.com>`
- `FRONTEND_URL=https://iaaffintel.com`
- `PASSWORD_RESET_MINUTES=30`
