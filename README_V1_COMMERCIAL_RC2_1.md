# AIAffiliate Intelligence — V1 Commercial RC2.1

Correção estrutural da reconexão TikTok após OAuth.

- Remove índices/constraints legados que tornavam `social_connections.platform` globalmente único.
- Mantém unicidade correta por `(company_id, platform)` para ambiente SaaS multiempresa.
- Callback TikTok agora reutiliza a conexão da empresa e adota registros legados com `company_id IS NULL`, evitando `UniqueViolation` durante reconexão.
- Preserva OAuth, scopes, Content Posting API, Direct Post/Draft e integração Pinterest da RC2.
