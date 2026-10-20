# RC8 — identificação do suporte, foto de perfil e menu adaptativo

## Alterações

1. **Atendimento:** respostas enviadas pela área administrativa aparecem como **Suporte**. A API também deixa de expor o nome real do atendente no campo de autor dessas mensagens. O histórico anterior recebe a mesma identificação ao ser consultado. Os identificadores de autoria continuam preservados internamente para auditoria.
2. **Meu perfil:** botão Enviar/Trocar foto com upload de JPG, PNG ou WebP de até 3 MB. A imagem é ajustada para 256×256, convertida em JPEG e salva no banco vinculada ao usuário. A foto aparece no perfil, no cabeçalho e no menu da conta. Também é possível removê-la e voltar às iniciais.
3. **Barra lateral:** botão para recolher/expandir no computador, mantendo a preferência no navegador. Quando recolhida, mostra ícones com nomes acessíveis e dicas de texto. Em telas de até 750 px, o menu fica oculto e pode ser aberto pelo botão de três pontos no cabeçalho. Pode ser fechado pelo X, pelo fundo, pela tecla Escape ou ao navegar. Com o menu aberto, a navegação por teclado permanece dentro dele.

## Atualização

Atualize backend e frontend. Na inicialização, o mecanismo existente cria a tabela nova `user_avatars`; o usuário do banco precisa manter a permissão de criar tabelas. Não é necessário alterar tabelas existentes, assinaturas, variáveis Stripe ou configurações de armazenamento. As fotos ficam no banco, preservadas entre reinicializações e deploys.

## Verificação

- 51 testes de backend aprovados: regressões RC5/RC6/RC7, nome público Suporte, imagem inválida, normalização, isolamento por usuário, upload e remoção.
- Interface testada em DOM simulado com React: recolher/expandir, persistência de preferência, menu móvel, fechamento por Escape e navegação, upload/remoção e atualização da foto no cabeçalho.
- Build de produção Next.js e TypeScript concluídos com as dependências do pacote anterior.
- Inicialização completa em SQLite temporário confirmou a criação da tabela e o bloqueio da foto sem autenticação. Não houve deploy nem alteração do banco de produção durante os testes.
