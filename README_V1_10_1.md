# AIAffiliateIntelligence V1.10.1

Correções e melhorias:
- Diagnóstico estruturado das variáveis ausentes da integração Mercado Livre.
- Tela de Integrações exibe quais variáveis precisam ser configuradas, sem expor segredos.
- Melhor espaçamento e hierarquia visual dos cards de Plano e assinatura.
- Card do plano atual com tonalidade e destaque próprios.
- Favicon com a nova identidade visual.
- Health/version: 1.10.1.

## Mercado Livre no Railway
Configure: MELI_CLIENT_ID, MELI_CLIENT_SECRET, MELI_REDIRECT_URI e TOKEN_ENCRYPTION_KEY.
O MELI_REDIRECT_URI deve ser HTTPS e corresponder exatamente ao cadastrado no DevCenter Mercado Livre.
Não coloque segredos no frontend nem no GitHub.
