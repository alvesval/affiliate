# V1.13.5 — fal.ai Queue URL fix + observabilidade

Correção da integração de geração de vídeo com fal.ai partindo da V1.13.4.

## Alterações
- Preserva `status_url` e `response_url` canônicos retornados pelo submit da fila fal.ai.
- O polling usa o `status_url` retornado pela própria fal.ai, evitando montar uma URL incorreta para endpoints de modelo compostos.
- O download do resultado usa o `response_url` retornado pela própria fal.ai.
- Validação de host das URLs da fila para evitar SSRF.
- Logs estruturados `[FAL]` no Railway para submit, status, resultado, download e erros HTTP.
- Nenhuma `FAL_KEY` é registrada nos logs.
- Mantido fallback para a construção anterior de URL para compatibilidade.

## Railway
Manter:
- `VIDEO_PROVIDER=fal`
- `FAL_KEY=<chave>`
- `FAL_VIDEO_MODEL=fal-ai/kling-video/v3/standard/text-to-video`

Após deploy, teste "Criar vídeo com IA" e acompanhe os logs `[FAL]`.
