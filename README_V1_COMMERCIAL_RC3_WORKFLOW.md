# AIAffiliate Intelligence v1.0 Commercial RC3 — Workflow

Base: RC2.1 TikTok Fix.

## Alterações desta versão
- Nova jornada visual da campanha: Produto e link → Conteúdo → Referências reais → Mídia → Aprovação → Canais → Publicação → Resultado.
- Novo endpoint `GET /api/v1/social/campaigns/{id}/workflow` com progresso, próxima ação e validações reais do banco.
- Normalização de estados de publicação para linguagem de produto.
- TikTok Draft: `SEND_TO_USER_INBOX` agora é persistido como `sent_to_tiktok` e exibido como **Enviado ao TikTok — Aguardando finalização no aplicativo TikTok**, em vez de permanecer indefinidamente como `processing`.
- Nenhum dado de performance/comissão/conversão fictício foi adicionado.
- Fluxos TikTok/Pinterest existentes foram preservados.

## Validação
- Backend validado com `python -m compileall`.
- O build do frontend não pôde ser executado neste ambiente porque as dependências Node do pacote não estavam instaladas e a instalação excedeu o limite do ambiente. Validar com `npm ci && npm run build` no pipeline/deploy antes de produção.
