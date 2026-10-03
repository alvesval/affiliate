# AIAffiliateIntelligence V1.11 — Commercial Hardening

- Remove o TRIAL da oferta comercial e cria plano Entrada a R$ 29/mês.
- Planos: Entrada R$29, Starter R$49, Pro R$99, Business R$199.
- Cadastro recebe o plano escolhido na Home e cria assinatura `incomplete`/pagamento pendente, sem trial automático.
- Home pública ganhou seção de planos e CTAs por plano.
- Stripe ganhou `STRIPE_PRICE_ENTRY`.
- `ensure_plans` agora sincroniza preços/limites existentes e desativa TRIAL da vitrine.
- Onboarding detecta Mercado Livre pela tabela OAuth real (`meli_oauth_tokens`), corrigindo o passo que permanecia cinza.
- Oportunidades explica que são calculadas automaticamente e leva ao catálogo para configurar link/comissão.
- Autopilot salva as regras antes de executar e usa o mesmo score dinâmico da tela Oportunidades, removendo dependência de `ProductScore` persistido.
- Limites comerciais incluem cotas separadas para IA de texto e vídeo para permitir controle de margem.

## Variáveis novas
`STRIPE_PRICE_ENTRY` deve receber o Price ID do plano Entrada no Stripe antes de ativar checkout real.

## Nota de custos de IA
As cotas de IA/vídeo desta versão são parâmetros comerciais iniciais. Antes do lançamento, medir custo real por geração e ajustar os limites. O plano Entrada não inclui vídeo IA mensal: vídeo fica por consumo/add-on para proteger margem.
