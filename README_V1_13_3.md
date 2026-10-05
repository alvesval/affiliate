# AIAffiliateIntelligence v1.13.3 — Recuperação segura de senha

## Incluído
- Link **Esqueci minha senha** na tela de login.
- Tela `/esqueci-senha` com resposta neutra para não revelar se um e-mail existe.
- Endpoint `POST /api/v1/saas/auth/forgot-password`.
- Tokens aleatórios de uso único; somente SHA-256 do token é persistido.
- Expiração configurável (30 minutos por padrão) e invalidação de links anteriores.
- Envio transacional via Resend.
- Tela `/redefinir-senha?token=...` com senha + confirmação.
- Endpoint `POST /api/v1/saas/auth/reset-password`.
- Auditoria de redefinição e invalidação de todos os tokens pendentes após sucesso.

## Variáveis de produção (backend/Railway)
```
RESEND_API_KEY=re_...
EMAIL_FROM=AIAffiliateIntelligence <noreply@iaaffintel.com>
PASSWORD_RESET_MINUTES=30
FRONTEND_URL=https://iaaffintel.com
```

Antes do primeiro envio em produção, verifique `iaaffintel.com` no provedor de e-mail transacional. O Cloudflare Email Routing usado para receber `admin@iaaffintel.com` é independente do envio transacional.
