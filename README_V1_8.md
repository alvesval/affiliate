# Affiliate Intelligence V1.8

## Escopo

A V1.8 evolui a base validada da V1.7 (R2 + TikTok Direct Post) com atribuição de afiliados, disclosure comercial e diagnóstico de publicação.

### 1. Links e etiquetas por variação/canal
- Cada `ContentVariant` passa a guardar `affiliate_url`, `affiliate_label` e `link_placement`.
- Novas campanhas copiam o link/etiqueta verificados do produto.
- TikTok deixa de inserir o URL cru na legenda de novas campanhas e usa CTA de perfil.
- Endpoint: `PUT /api/v1/social/variants/{variant_id}/affiliate-link`.
- A etiqueta é validada no padrão informado pelo Mercado Livre: até 30 caracteres, letras minúsculas e números, sem espaços.
- A V1.8 **não cria etiquetas no Mercado Livre** e não usa redirecionador próprio. O link deve continuar sendo gerado oficialmente no Portal/Barra de Afiliados com a etiqueta desejada.

### 2. TikTok Commercial Disclosure
O modal agora envia os campos suportados pelo Direct Post:
- `brand_content_toggle`
- `brand_organic_toggle`
- `is_aigc`

Para conteúdo de afiliado de terceiros, `brand_content_toggle` é apresentado marcado por padrão. A UI e o backend bloqueiam a combinação `brand_content_toggle=true` + `SELF_ONLY`, porque o TikTok não aceita Branded Content nessa visibilidade.

> Durante sandbox/cliente não auditado, o TikTok restringe Direct Post à visualização privada. Portanto, o teste técnico privado da V1.7 continua válido, mas um post comercial real deve ser feito somente em uma combinação permitida após a auditoria/aprovação do app.

### 3. Status TikTok detalhado
`Publication` passa a persistir:
- `tiktok_status`
- `tiktok_fail_reason`
- `uploaded_bytes`
- `public_post_ids`

A tela mostra status, publish id, bytes transferidos e post id quando disponibilizado.

### 4. Duração real da mídia
O navegador lê a duração do vídeo selecionado e envia ao backend no upload. A campanha é sincronizada com a duração real arredondada da mídia, eliminando casos como campanha 30s com MP4 de 15s.

## Banco de dados
A migração idempotente em `app/core/migrations.py` adiciona as colunas automaticamente no startup, preservando os dados da V1.7.

## Deploy
1. Faça backup/commit da V1.7 atual.
2. Substitua os arquivos da aplicação pelos desta V1.8, preservando `.env` e `.git` locais.
3. `git add . && git commit -m "V1.8 - affiliate attribution and TikTok disclosure" && git push origin main`
4. Confirme `/health` retornando `1.8.0`.
5. Abra uma campanha e valide primeiro os novos campos sem criar nova publicação real.

As variáveis R2 já usadas na V1.7 permanecem as mesmas. Nenhum segredo novo é necessário para esta versão.
