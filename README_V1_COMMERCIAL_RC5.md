# AIAffiliateIntelligence — Commercial RC5

Base: Commercial RC4 Central de Campanhas.

## Ajustes
- Gancho, Roteiro e Legenda editáveis, com botão Salvar textos e indicação de alterações não salvas.
- Salvar alterações e recriar texto retiram a aprovação da campanha; é necessário revisar e aprovar novamente.
- Recriar texto pede confirmação antes de substituir os textos salvos.
- Aprovação e abertura do modal de publicação impedidas quando há textos alterados sem salvar.
- Edição de campanhas com publicação na fila, em processamento ou concluída é recusada para preservar o conteúdo já enviado. Para esses casos, criar nova campanha.
- Roteiros novos/recriados passam a conter fala pronta, sem instruções internas. Gancho Pinterest identifica o produto. Textos existentes só mudam com edição ou Recriar texto.
- Capa Pinterest convertida a JPEG RGB usando a foto real armazenada, com transparência sobre fundo branco, orientação corrigida e limite de 2000 pixels.
- Capa assinada no momento da execução; falhas na leitura/conversão aparecem como erro da publicação.
- Publicações enviadas ou em andamento não podem ser reexecutadas pelo botão Publicar/testar.

## Atualização
1. Atualizar backend e frontend com este pacote e executar os builds/deploys habituais.
2. Preservar variáveis de ambiente e banco. Não há migração de schema nesta versão.
3. Abrir campanha, editar Gancho/Roteiro/Legenda, clicar Salvar textos e aprovar novamente.
4. Para Pinterest, adicionar foto real em Imagens reais do produto ou usar Usar foto oficial do produto. Definir a referência principal correta antes do envio.
5. Em acesso Standard, manter PINTEREST_ACCESS_STATUS=standard. Esta atualização não altera credenciais.
6. Para publicação com erro de capa, adicionar/conferir a referência e usar Publicar/testar. Se editar textos, aprovar novamente antes de tentar.

## Validação
- Compilação Python e verificação sintática TSX concluídas.
- Seis testes locais aprovados: PNG/WebP/JPEG, transparência, entrada inválida, retirada de aprovação, bloqueio de edição com publicação ativa/concluída e roteiro sem instruções internas.
- Testes de aprovação usam funções isoladas e mocks; não substituem teste de integração com banco.
- Build completo Next.js e teste de publicação real Pinterest dependem do ambiente de deploy. As dependências frontend do pacote-base não estão instaladas neste ambiente.
