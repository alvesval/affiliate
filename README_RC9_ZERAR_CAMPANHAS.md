# RC9 — zerar o consumo de campanhas e publicações

O bloqueio 20/20 da criação manual corresponde ao contador mensal de campanhas. As versões anteriores permitiam ajustar somente publicações. Esta atualização acrescenta o ajuste de campanhas, mantendo os controles separados.

## Para liberar os testes
1. Atualize backend e frontend no Railway.
2. Entre em **Administração → Clientes → Detalhar** na empresa usada nos testes.
3. Em **Ajustar consumo de campanhas**, clique em **Zerar campanhas**.
4. Preencha um motivo, como "Testes administrativos de publicação", e clique em **Salvar ajuste de consumo**.
5. Se a cota de publicações também estiver no limite, repita no bloco **Ajustar consumo de publicações**.
6. Volte ao Estúdio IA e tente criar/publicar novamente.

O botão Zerar preenche o novo consumo com zero; o ajuste só é aplicado após salvar com o motivo. Também é possível reduzir para outro valor não negativo.

A alteração é exclusiva dos administradores da plataforma e do mês atual. O consumo anterior é conferido no servidor para impedir a sobrescrita de um valor alterado enquanto o formulário estava aberto. Cada ajuste registra usuário, empresa, período, motivo e valores anterior/novo na auditoria.

Os totais históricos de campanhas e publicações continuam iguais, pois os registros existentes não são apagados. Somente o consumo que controla a cota mensal é reduzido. Plano, assinatura, Stripe, consumo de IA e outras empresas permanecem inalterados. A assinatura continua precisando estar ativa para usar os recursos pagos. O pacote preserva os recursos RC7/RC8 de suporte, foto e menu responsivo.

Não há nova tabela ou migração para este ajuste.

Validação: 59 testes de backend aprovados, build de produção Next.js/TypeScript concluído e teste de interface em DOM simulado verificando os dois botões, os dados enviados e a atualização dos contadores. Nenhum banco de produção foi alterado durante esta preparação.
