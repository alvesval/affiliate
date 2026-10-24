# Affiliate Intelligence V1.8.1

Correção incremental sobre a V1.8.

## Ajustes
- Persistência explícita da configuração de link/etiqueta por variante.
- Novo campo `affiliate_configured_at` com migração automática.
- `Salvar link` agora exibe Salvando, sucesso, alterações não salvas e erro local.
- A resposta salva é refletida imediatamente na tela.
- Recarregar a campanha restaura URL, etiqueta e uso a partir do banco.
- Publicação é bloqueada enquanto a configuração de link da variante não tiver sido salva explicitamente.
- Etiqueta ML continua opcional.
- Health/version atualizado para 1.8.1.

## Teste recomendado
1. Digite uma etiqueta de teste válida, como `tiktokps0301`.
2. Clique em Salvar link e confirme `Configuração salva no banco`.
3. Pressione F5 e abra a campanha novamente.
4. Confirme que a etiqueta reaparece.
5. Para um link criado sem etiqueta no Mercado Livre, apague a etiqueta e salve novamente; vazio é válido.
