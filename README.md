# Affiliate Intelligence V1

Base profissional para operação de afiliados com **Next.js/TypeScript + Python/FastAPI + PostgreSQL**.

## V1
- Dashboard web responsivo
- API FastAPI documentada em `/docs`
- PostgreSQL via Docker Compose
- Catálogo de produtos
- Histórico/estrutura para preços e scores
- Score inicial explicável (desconto + comissão + ticket)
- Seed de demonstração
- Estrutura de integrações Mercado Livre/SHEIN
- Sem credenciais reais no repositório

## Executar com Docker
1. Copie `.env.example` para `.env`.
2. Troque `JWT_SECRET` e, para produção, as senhas.
3. Execute `docker compose up --build`.
4. Frontend: http://localhost:3000
5. API/docs: http://localhost:8000/docs

## Desenvolvimento sem Docker
Backend usa `DATABASE_URL`; para teste local também aceita SQLite pelo valor padrão de configuração.

## Próximas versões
Autenticação/multiempresa, Alembic, providers reais, tracking de cliques/conversões, conteúdo, score calibrável, analytics e ML após acumular dados suficientes.

> Observação: integrações reais dependem das credenciais e das APIs/feeds efetivamente disponibilizados pelas plataformas à conta do afiliado.

## OAuth Mercado Livre (versão incremental V1.1)

1. Configure `.env` com `ADMIN_SETUP_KEY`, `MELI_CLIENT_ID`, `MELI_CLIENT_SECRET`, `MELI_REDIRECT_URI` e `TOKEN_ENCRYPTION_KEY`. Nunca compartilhe `.env`.
2. Gere uma chave Fernet executando `docker compose run --rm backend python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` e cole o resultado em `TOKEN_ENCRYPTION_KEY`.
3. Use uma chave aleatória forte para `ADMIN_SETUP_KEY` (por exemplo, `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
4. Inicie `docker compose up --build -d` e `cloudflared tunnel --url http://localhost:8000`. Configure `MELI_REDIRECT_URI=https://SEU-TUNEL.trycloudflare.com/api/integrations/mercadolivre/callback` e registre a **mesma URI** no DevCenter; reinicie o backend após alterar `.env`.
5. Em `http://localhost:3000/integracoes`, informe a chave administrativa e clique **Conectar Mercado Livre**. O Mercado Livre retornará ao callback, que gravará tokens criptografados no PostgreSQL.
6. Volte à página e informe novamente a chave administrativa para consultar o status. O campo não é salvo no browser.

**Limitações e segurança:** Esta V1 não tem login nem multiusuário; use a integração somente em ambiente de desenvolvimento controlado. As rotas de administração exigem `X-Admin-Key`, mas o callback OAuth é público por necessidade e protegido por state de uso único e PKCE. Não exponha `/docs` e outros endpoints não autenticados com dados reais; use o túnel apenas durante o teste. O botão de renovação usa refresh token; renovação automática no cliente de catálogo e importação de produtos ainda serão adicionadas. `disconnect` remove tokens locais, não revoga autorização no provedor. A URI temporária muda quando o túnel reinicia. O token e a chave de criptografia devem permanecer persistentes; perder a chave impede ler os tokens. Não altere a chave Fernet após autorizar sem migrar os dados. Os dados de demonstração existentes não são produtos reais.
"# affiliate" 
