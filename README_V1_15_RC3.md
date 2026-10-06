# AIAffiliate Intelligence v1.15 RC3

## Ajustes desta release

- Pinterest liberado na interface quando as credenciais OAuth estiverem configuradas.
- Status padrão do acesso Pinterest atualizado de `pending_trial` para `trial`.
- OAuth Pinterest solicita somente os escopos necessários nesta etapa: `boards:read`, `pins:read`, `pins:write`, `user_accounts:read`.
- Mercado Livre conectado passa a exibir `Reconectar Mercado Livre`.
- Botões da tabela Oportunidades ficaram compactos, alinhados e sem quebra de texto.
- Coluna Ação ganhou largura consistente para evitar o desalinhamento visto em resoluções largas.

## Railway

Configurar:

```env
PINTEREST_CLIENT_ID=1620483
PINTEREST_CLIENT_SECRET=<segredo configurado diretamente no Railway>
PINTEREST_REDIRECT_URI=https://affiliate-production-9066.up.railway.app/api/v1/social/pinterest/callback
PINTEREST_ACCESS_STATUS=trial
```

Nunca versionar o `PINTEREST_CLIENT_SECRET`.
