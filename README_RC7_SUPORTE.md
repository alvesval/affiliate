# RC7 — Central de Suporte

## Como usar

### Cliente
1. Abra **Configuração → Ajuda e suporte**.
2. Clique em **Novo chamado**, preencha assunto, categoria e mensagem. O número da campanha é opcional e deve pertencer à empresa atual.
3. Acompanhe o protocolo, o histórico e as respostas. Use a conversa para complementar informações.
4. Marque como resolvido quando concluído. Uma nova mensagem pública reabre um chamado resolvido.

Os membros autenticados da mesma empresa podem acompanhar os chamados desse workspace. Cada empresa vê apenas os próprios chamados. O acesso ao suporte permanece disponível com assinatura inativa.

### Administrador da plataforma
1. Abra **Administração → Atendimento**.
2. Busque por protocolo, assunto, nome da empresa ou e-mail do solicitante. Filtre por status, categoria e prioridade.
3. Abra o chamado e envie uma resposta pública ou marque **Observação interna** para registrar informações exclusivas da equipe.
4. Atualize status e prioridade conforme o atendimento avança.

As permissões administrativas reutilizam `is_super_admin` e `PLATFORM_ADMIN_EMAILS`, já usados nas áreas Clientes e Planos. Ser OWNER ou ADMIN de uma empresa, por si só, não concede acesso aos chamados de outras empresas.

## Regras
- Status: Aberto, Em atendimento, Aguardando cliente e Resolvido.
- Resposta pública do atendimento muda o status para Aguardando cliente.
- Resposta do cliente em chamado resolvido ou aguardando cliente muda o status para Aberto.
- Observação interna não muda o status e não aparece na API nem na conversa do cliente.
- Prioridades: Baixa, Normal, Alta e Urgente; alteradas somente pelo administrador da plataforma.
- Contadores no menu representam mensagens não lidas, com leitura individual por usuário. Listas e conversa atualizam a cada 30 segundos quando a aba está visível; o botão Atualizar também permite consulta imediata.
- Novas mensagens e mudanças de status/prioridade ficam registradas na auditoria existente. Mensagens são exibidas como texto, sem interpretar HTML.
- Esta versão atende dentro do aplicativo. Não envia e-mail/WhatsApp e não inclui anexos.

## Atualização no Railway
1. Publique o backend e o frontend deste pacote, preservando as variáveis e o banco existentes.
2. Ao iniciar o backend, o mecanismo já existente `Base.metadata.create_all` cria as tabelas novas: `support_tickets`, `support_messages` e `support_reads`, além dos índices. O usuário do banco precisa de permissão para criar tabelas, como nas atualizações anteriores.
3. Nenhuma configuração Stripe é alterada. Não há necessidade de executar UPDATE/DELETE em dados existentes ou comprar outra assinatura.
4. Abra o suporte em uma conta de cliente, envie um chamado e responda pela área de Atendimento do administrador. Confirme que outra empresa não enxerga a conversa.

## Validação
- 41 testes automatizados aprovados, incluindo regressões RC5/RC6, acesso entre empresas, notas internas, permissão administrativa, filtros, validação de entrada, leitura individual e reabertura.
- Fluxos de interface executados em DOM simulado com React: abertura de conversa, envio de resposta, criação de chamado, observação interna administrativa e resolução.
- Inicialização completa do backend em banco SQLite temporário: novas tabelas criadas, endpoint health e bloqueio de acesso sem autenticação verificados.
- Build de produção do frontend e validação TypeScript concluídos com o package-lock fornecido. Existe aviso de compatibilidade CSS no arquivo anterior ao módulo de suporte.
- Não houve acesso a contas de clientes, alteração de banco de produção, envio de mensagens reais ou deploy durante esta preparação.
