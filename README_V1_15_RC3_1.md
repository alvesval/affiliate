# AIAffiliate Intelligence v1.15 RC3.1

Correção de build do frontend.

- Corrigido JSX inválido em `frontend/src/app/(workspace)/conteudos/page.tsx` no modal de publicação multicanal.
- Removido fragmento React redundante/mal fechado introduzido na RC3 ao adicionar a seleção de Board do Pinterest.
- Mantidas as alterações da RC3 para Pinterest e alinhamento dos botões de Oportunidades.

Validação local: a correção foi aplicada no ponto exato indicado pelo erro do webpack. O build Next.js completo não pôde ser executado neste ambiente porque as dependências do frontend (`next`) não estão instaladas.
