# v1.13.3 build fix

Correção do build do frontend após inclusão da recuperação de senha.

- Corrigidos imports `@/lib/api` nas páginas de autenticação para o padrão relativo já utilizado pelo projeto (`../../../lib/api`).
- Arquivos corrigidos: login, esqueci-senha e redefinir-senha.
- Confirmado que não restam imports `@/...` em `frontend/src`.
- Backend validado com `python -m compileall`.

Observação: o build Next.js não pôde ser executado neste ambiente porque as dependências Node não estavam disponíveis localmente.
