# AIAffiliateIntelligence V1.10 — Workspace UX

- Cabeçalho global em todas as telas autenticadas com empresa/workspace, plano, usuário e perfil.
- Menu do usuário com Meu perfil, Segurança e Sair.
- Nova tela Meu perfil e atualização do nome.
- Nova tela Segurança com troca de senha validando a senha atual e usando o hash robusto Argon2id.
- Logo oficial aplicado ao sidebar, login e cadastro.
- Logo de login/cadastro volta para a home ao clicar.
- Redução do espaço superior das telas de trabalho; conteúdo começa logo abaixo do cabeçalho.
- Login com feedback de carregamento e erro de rede.

Observação: nesta versão o avatar usa iniciais como fallback seguro. Upload persistente de foto de perfil pode ser incluído depois via R2, sem armazenar a imagem no JWT ou no banco.
