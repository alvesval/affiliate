# RC6 — ajuste de cota e editor de campanhas

## Administração
Administração → Clientes → Detalhar → Ajustar consumo de publicações.
Informe o novo consumo (zero para devolver toda a cota mensal), preencha o motivo e clique em Salvar ajuste de consumo. Exemplo: reduzir 10/10 para 0/10 libera dez novas publicações no mês atual.
Apenas administradores da plataforma podem ajustar. O plano, assinatura, cobrança Stripe e histórico de publicações são mantidos. O ajuste registra administrador, empresa, mês, valor anterior, valor novo e motivo na auditoria existente. Outros consumos não mudam. Se a cota mudar enquanto o formulário estiver aberto, reabra os detalhes para atualizar antes de salvar.

## Campanhas
Clicar em Abrir campanha abre o editor em um modal com rolagem própria. É possível editar nome, objetivo, formato, duração, tom e público, além das funções existentes de textos, links e mídia. Cada seção tem seu botão de salvar.
Alterações no direcionamento preservam textos e mídia; revise-os e aprove novamente. Campanhas já na fila, em processamento ou publicadas mantêm o bloqueio de alteração de conteúdo. Fechar com alterações de texto ou dados da campanha não salvas solicita confirmação.

## Instalação e validação
Atualize o backend e o frontend no Railway. Não requer migração ou alteração de variáveis Stripe. O pacote mantém os ajustes RC5 do Pinterest e dos textos.
Verificação: 21 testes aprovados (regressão RC5, permissões administrativas, liberação da cota, auditoria, dados desatualizados, preservação do Stripe, isolamento entre empresas e edição de campanha); TypeScript sem erros e compilação Python aprovada. Não foi executado um pagamento real nem publicação em conta externa durante a validação. A validação de tipos usou dependências isoladas; não foi executado o build completo com o conjunto original de dependências do projeto.
