# AIAffiliateIntelligence V1.9.2 — Cadastro resiliente

Correções desta versão:

- adiciona campo **Confirmar senha** no cadastro;
- valida senha mínima e igualdade das duas senhas antes de chamar a API;
- adiciona estado **Criando workspace...** e bloqueio contra duplo clique;
- trata erro de rede/CORS/backend e exibe mensagem ao usuário;
- trata respostas não-JSON sem quebrar silenciosamente;
- timeout de 20 segundos com mensagem explícita;
- redireciona com `router.replace` + `router.refresh` após sucesso;
- adiciona link para Login;
- mantém a confirmação de senha somente no frontend: a API recebe apenas `password`.

## Diagnóstico

Se o botão agora mostrar `Não foi possível conectar à API`, conferir no build do Cloudflare:

`NEXT_PUBLIC_API_URL=https://affiliate-production-9066.up.railway.app`

E conferir o backend em `/health`, que deve responder versão `1.9.2`.

CORS já inclui `https://iaaffintel.com` e o domínio workers.dev legado.
