# AIAffiliateIntelligence v1.15 RC3.5 — Pinterest Trial/Standard

## Pinterest
- `PINTEREST_ACCESS_STATUS=trial`: OAuth token exchange and API calls use `api-sandbox.pinterest.com`.
- Trial/Sandbox publishes an **Image Pin** using the real product reference image. Pinterest Sandbox does not support Video Pins.
- If the Sandbox has no board, the publication modal can create `AIAffiliate Sandbox`.
- `PINTEREST_ACCESS_STATUS=standard`: production API is selected automatically and the existing Video Pin flow is enabled.
- OAuth scopes: `boards:read, boards:write, pins:read, pins:write, user_accounts:read`.
- Sandbox and production tokens are different. Reconnect Pinterest after changing the access status.
- Signed cover URLs are refreshed at execution time, preventing scheduled Pinterest publications from failing because a 1-hour URL expired.

## Deployment
Current Trial:
`PINTEREST_ACCESS_STATUS=trial`

After Pinterest approves Standard:
`PINTEREST_ACCESS_STATUS=standard`
Then reconnect Pinterest once so a production token is issued.
