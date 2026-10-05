# AIAffiliateIntelligence v1.13.2 — Video Provider

## Alterações
- Camada `VideoProvider` desacopla o SaaS de um fornecedor específico de vídeo.
- Primeiro provider: fal.ai via Queue API.
- Modelo padrão configurável: `fal-ai/kling-video/v3/standard/text-to-video`.
- Geração vertical 9:16 e assíncrona.
- A franquia mensal de vídeo não é consumida quando a solicitação apenas entra na fila ou falha ao iniciar.
- O consumo é confirmado após a geração concluir e o arquivo ser anexado à variação.
- Polling repetido do mesmo job não cobra novamente.
- `/health` informa provider/modelo de vídeo ativos.

## Railway
Adicionar:
```
VIDEO_PROVIDER=fal
FAL_KEY=<sua chave fal.ai>
FAL_VIDEO_MODEL=fal-ai/kling-video/v3/standard/text-to-video
```
`OPENAI_API_KEY` continua necessário para geração de texto. `OPENAI_VIDEO_MODEL` é legado.
