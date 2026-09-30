# Affiliate Intelligence V1.3 — Importação manual de afiliados

Atualização incremental da V1.2, sem apagar o PostgreSQL nem substituir o OAuth existente.

## Novidades
- `POST /api/v1/affiliates/mercadolivre/batch` com autenticação administrativa `X-Admin-Key`.
- Importação de até 100 pares de URL original e link remunerado oficial por requisição.
- Campos: título, preço e comissão informados pelo usuário, etiqueta e ID MLB opcional.
- Identificação idempotente por ID MLB, URL original ou link remunerado, sem consultar anúncios de terceiros com a API de vendedor.
- URL HTTPS com hosts autorizados; nenhum redirecionamento de link de afiliado é seguido.
- Campos `affiliate_label`, `affiliate_source`, `affiliate_verified_at` com migração aditiva.
- Nova seção de importação em Catálogo; histórico de preço não é fabricado para cadastros manuais.

## Instalação sem perda de dados
1. Faça backup do PostgreSQL e guarde seu `.env` existente em local seguro.
2. Copie os arquivos da V1.3 sobre a pasta da V1.2. Não substitua seu `.env` pelo `.env.example`.
3. Execute `docker compose up --build -d` na pasta do projeto. NÃO execute `docker compose down -v`.
4. Abra `http://localhost:3000/produtos` e use **Importação de links remunerados**.

Formato: `URL original | Link de afiliado | Título | Preço | Comissão (%) | Etiqueta | ID MLB`

Exemplo fictício (substitua por links oficiais reais):
`https://www.mercadolivre.com.br/produto-exemplo | https://meli.la/SEU_LINK_REAL | Produto exemplo | 89,90 | 12 | instagram | MLB123456789`

Os três primeiros campos são obrigatórios. Preço, comissão, etiqueta e ID são opcionais. Não inclua o caractere `|` dentro de um campo. A comissão não é calculada automaticamente nem verificada pelo programa.

**Limites:** não há integração com uma API oficial de afiliados, scraping, geração automática de link, descoberta de terceiros, publicação automática ou confirmação de vendas. A seção permite cadastrar o vínculo fornecido pelo painel, para posterior preparação de conteúdo.

**Segurança:** a chave administrativa é exigida no backend; não publique a API com chave fraca. URLs e textos fornecidos pelo usuário são tratados como dados, não instruções. Não inclua segredos em repositórios.
