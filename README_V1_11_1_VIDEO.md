# V1.11.1 — restauração da criação de vídeo por IA

- Reativado o router `/api/v1/ai-studio` no backend.
- Restaurado o botão `Criar vídeo com IA` na tela de Conteúdos.
- Quando já existe mídia, o botão passa a `Recriar vídeo com IA` e pede confirmação antes de substituir.
- Polling de status da geração com progresso no próprio botão.
- Upload manual `Adicionar vídeo` / `Trocar vídeo` foi preservado.
- Ao concluir, o vídeo gerado é armazenado no R2 e vinculado à variação.
- Corrigido o backend para permitir substituir mídia existente por uma nova geração IA.

Observação de validação: os arquivos Python foram compilados com sucesso. O build do frontend não pôde ser executado neste ambiente porque as dependências Node não estão instaladas (`next: not found`).
