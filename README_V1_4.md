# Affiliate Intelligence V1.4

## Objetivo
A V1.4 troca o fluxo principal técnico por um fluxo orientado a usuário leigo: **colar link → analisar → confirmar somente o que faltar → salvar**.

## Principais mudanças
- Assistente de produto aceita URL oficial do Mercado Livre ou `meli.la`.
- Resolve redirecionamentos somente entre domínios oficiais permitidos.
- Tenta obter ID MLB, título, imagem e preço somente quando esses dados estiverem realmente expostos na URL/página pública.
- Detecta se o link informado é remunerado (`meli.la` ou `/social/`).
- Comissão continua sendo confirmada pelo usuário: a V1.4 não inventa nem tenta decodificar remuneração.
- Importação por `|` foi movida para **Importação avançada em lote**.
- Mantém PostgreSQL, OAuth, catálogo, histórico e conteúdo da V1.3.
- Novo serviço `AffiliateProvider` prepara a arquitetura para provedores oficiais futuros.

## Atualização
Preserve o `.env` da instalação atual e o volume PostgreSQL.

```bash
docker compose up --build -d
```

Não execute `docker compose down -v` se deseja preservar o banco.

## Segurança
O analisador possui whitelist de hosts e não segue redirecionamentos para domínios arbitrários. Não acessa endpoints privados do painel de afiliados.
