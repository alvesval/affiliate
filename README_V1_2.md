# Affiliate Intelligence V1.2 — catálogo controlado + conteúdo rascunho

## Instalação (preserva o banco)

1. Faça backup do ZIP atual e do volume PostgreSQL. **Não sobrescreva seu `.env`**.
2. Substitua os arquivos de código pelos desta versão.
3. `docker compose up --build -d` — **não use `down -v`**.
4. Confirme `http://localhost:8000/health` e `http://localhost:3000/produtos`.

## Importação real

- Acesse Integrações, confirme o status OAuth.
- Em Produtos, informe sua `ADMIN_SETUP_KEY` e um ou mais IDs de anúncio `MLB...` separados por vírgula ou linha.
- A importação consulta **somente anúncios específicos** via API `/items/{id}`. Não foi implementada busca pública por palavras-chave nem feed afiliado: a disponibilidade depende das permissões e regras atuais da API.
- HTTP 403/404/429 aparece por item, sem inventar produtos ou preços.
- Produtos importados são gravados em `products` e snapshots em `product_prices`.
- `original_price` de anúncios não é usado como histórico comprovado. São necessárias pelo menos três coletas para comparação histórica preliminar.
- Link de afiliado e taxa de comissão são preenchidos **manualmente com dados do programa de afiliados**; nunca são inferidos da API de vendedor.
- Conteúdos são **rascunhos determinísticos** com identificação publicitária; nenhum post é publicado automaticamente.

## Segurança e limites

- Importação, edição de afiliado e geração de rascunho exigem `X-Admin-Key`. O frontend não persiste a chave.
- O catálogo de leitura é público na V1.2; não exponha dados privados. Para SaaS multiusuário, implementar login, RBAC, isolamento por empresa, auditoria e migrations Alembic antes de produção.
- O túnel HTTPS temporário expõe o backend; mantenha-o somente durante testes.
- A migração de colunas da V1 é idempotente, mas **não** resolve duplicatas antigas. Não se adiciona índice único a dados históricos potencialmente duplicados.
- O score é **heurística preliminar**, não previsão de venda; só aparece para produtos com link e comissão cadastrados.
- Não há integração oficial de afiliados SHEIN/Mercado Livre, nem automação de redes sociais, nesta entrega.
