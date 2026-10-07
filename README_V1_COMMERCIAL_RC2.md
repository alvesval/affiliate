# AIAffiliate Intelligence v1.0 Commercial RC2

TikTok Production Integration hardening on top of Commercial RC1.

## Included
- OAuth requests `user.info.basic`, `video.publish` and `video.upload`.
- Creator Info is queried before publication.
- Human consent remains mandatory.
- Direct Post with TikTok privacy / interaction / commercial-content / AIGC controls.
- Draft upload mode using TikTok inbox init endpoint.
- Persisted `tiktok_publish_mode` (`direct` or `draft`) with idempotent DB migration.
- Existing FILE_UPLOAD transfer and publish status polling retained.
- Pinterest RC3.6 flow preserved.

## Deployment note
Because an existing TikTok connection may have been authorized before `video.upload` was requested, disconnect and reconnect TikTok once after deploying RC2 so the stored token contains all approved scopes. Do not rotate the client secret.

## Test sequence
1. Deploy backend/frontend.
2. Disconnect/reconnect TikTok through Integrations.
3. Open an approved campaign with TikTok video.
4. Test Direct Post with SELF_ONLY while the Direct Post audit is pending.
5. Check the returned publish_id and poll Status until terminal state.
6. Test Draft mode separately and finish the post inside TikTok.
