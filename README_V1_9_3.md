# AIAffiliateIntelligence V1.9.3 — Robust Password Security

## Correção principal
A V1.9.2 podia retornar HTTP 500 no cadastro por incompatibilidade entre `passlib 1.7.4` e versões recentes do backend `bcrypt` durante a inicialização/verificação interna do Passlib.

## Nova estratégia
- Novas senhas: **Argon2id** via `argon2-cffi`.
- Nenhuma senha é truncada silenciosamente.
- O contrato de cadastro continua aceitando de 8 a 128 caracteres.
- Hashes antigos bcrypt continuam válidos para login.
- Após um login bem-sucedido com hash bcrypt legado, o hash é migrado automaticamente para Argon2id.
- Verificação bcrypt legada é feita diretamente com `bcrypt`, sem Passlib.
- Login de e-mail inexistente executa uma verificação Argon2 dummy para reduzir diferença óbvia de timing para enumeração de usuários.
- Erro de senha continua retornando 401 genérico, sem informar se o e-mail existe.

## Dependências
Removido:
- `passlib[bcrypt]==1.7.4`

Adicionado:
- `argon2-cffi==23.1.0`
- `bcrypt==4.2.1` (somente compatibilidade de hashes legados)

## Deploy
1. Fazer commit/push desta versão.
2. Railway deve reconstruir a imagem e instalar as novas dependências.
3. Confirmar `GET /health` retornando `version: 1.9.3`.
4. Repetir o cadastro pelo Swagger ou pela tela `Criar empresa`.
5. Um cadastro novo deve persistir um `password_hash` iniciado por `$argon2id$`.

Não é necessária migração de banco para esta correção.
