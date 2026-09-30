# Affiliate Intelligence V1.5 — Social Publishing

Evolução da V1.4 sem remoção de dados existentes.

## Implementado
- Estúdio orientado a campanha, com seleção visual do produto afiliado (sem digitar ID interno).
- Campanha multicanal: Instagram, TikTok, YouTube Shorts e Pinterest.
- Objetivo, formato, duração 15/30/60 s, tom e público-alvo.
- Variações por rede com gancho, roteiro, legenda, CTA e hashtags.
- Aprovação humana obrigatória antes de fila/agendamento.
- Entidades persistentes `content_campaigns`, `content_variants`, `publications`, `social_connections` e `social_oauth_attempts`.
- Tela Integrações com status das redes sociais.
- TikTok Web OAuth 2.0 com `state`, tokens criptografados e escopos `user.info.basic,video.publish`.
- TikTok Content Posting API Direct Post para vídeo por URL HTTPS pública.
- Histórico e status de publicação, erro, retry e ID externo.
- Providers de Instagram, YouTube Shorts e Pinterest preparados no domínio, porém sem fingir publicação: retornam erro explícito até a ativação oficial de OAuth/permissões.

## TikTok
Cadastre uma aplicação no TikTok for Developers, habilite Login Kit e Content Posting API e configure no `.env`:

```
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_REDIRECT_URI=https://SEU-DOMINIO/api/v1/social/tiktok/callback
FRONTEND_URL=http://localhost:3000
```

O redirect web do TikTok precisa ser HTTPS, absoluto, estático e igual ao cadastrado no portal. Em cliente não auditado, o TikTok restringe conteúdo publicado pela API a visualização privada. A V1.5 usa `SELF_ONLY` por segurança durante a fase de integração.

Para Direct Post com `PULL_FROM_URL`, informe no Estúdio uma URL HTTPS pública de vídeo que atenda aos requisitos do TikTok. A V1.5 não inventa nem hospeda vídeo.

## Atualização
Preserve seu `.env` e banco PostgreSQL. Execute:

```
docker compose up --build -d
```

Não use `docker compose down -v` se quiser preservar o volume do PostgreSQL.

## Próximos passos de produção
1. Autenticação/RBAC e multi-tenant por empresa/usuário (substituir ADMIN_SETUP_KEY na experiência SaaS).
2. Ativar OAuth/publicação real de Meta/Instagram, YouTube e Pinterest após criação e aprovação dos respectivos apps.
3. Storage próprio/CDN para mídias e geração visual de vídeos/imagens.
4. Worker durável (Redis/Celery) para execução automática de agendamentos. Nesta versão a fila é persistida e a execução pode ser disparada pelo botão `Publicar/testar`; não há processo em background fingindo agendamento automático.
5. Webhooks/status do TikTok e analytics de clique/conversão.
