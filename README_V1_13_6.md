# AIAffiliateIntelligence v1.13.6

Base: v1.13.5.

## Alteração
- Player HTML5 de vídeo dentro da tela de conteúdo para revisão antes da aprovação/publicação.
- A mídia privada armazenada no R2 é carregada por endpoint autenticado do backend; a chave do objeto não é exposta ao navegador.
- Mantidos nome, tamanho, tipo, duração, remoção, recriação por IA e troca manual.
- Estados de carregamento e erro da prévia.

## Segurança
O endpoint `/api/v1/social/variants/{variant_id}/media/content` valida o usuário e `company_id` antes de ler o objeto no storage.
