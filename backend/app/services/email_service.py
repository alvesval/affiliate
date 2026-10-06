import json
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailDeliveryError(RuntimeError):
    pass

def _mask_email(value: str) -> str:
    try:
        local, domain = value.split('@', 1)
        visible = local[:2] if len(local) > 2 else local[:1]
        return f"{visible}***@{domain}"
    except Exception:
        return "***"

def send_password_reset_email(to_email: str, reset_url: str) -> str:
    if not settings.resend_api_key:
        logger.error('[EMAIL] Resend não configurado: RESEND_API_KEY ausente')
        raise EmailDeliveryError('RESEND_API_KEY não configurada')

    payload = {
        'from': settings.email_from,
        'to': [to_email],
        'subject': 'Redefinição de senha — AIAffiliateIntelligence',
        'html': f'''<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#14233a">
          <h2>Redefinição de senha</h2>
          <p>Recebemos uma solicitação para redefinir a senha da sua conta.</p>
          <p><a href="{reset_url}" style="display:inline-block;padding:12px 18px;background:#2563eb;color:white;text-decoration:none;border-radius:8px">Redefinir minha senha</a></p>
          <p>Este link expira em {settings.password_reset_minutes} minutos e pode ser usado apenas uma vez.</p>
          <p>Se você não solicitou a alteração, ignore esta mensagem.</p>
        </div>'''
    }
    req = Request(
        'https://api.resend.com/emails',
        data=json.dumps(payload).encode(),
        method='POST',
        headers={
            'Authorization': f'Bearer {settings.resend_api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'AIAffiliateIntelligence/1.13.4',
        },
    )

    masked = _mask_email(to_email)
    logger.info('[EMAIL] Iniciando envio de recuperação de senha via Resend para %s; from=%s', masked, settings.email_from)
    try:
        with urlopen(req, timeout=15) as response:
            body = response.read().decode('utf-8', errors='replace')
            if response.status >= 300:
                logger.error('[EMAIL] Resend recusou envio para %s: HTTP %s body=%s', masked, response.status, body[:1000])
                raise EmailDeliveryError(f'Falha no envio: HTTP {response.status}')
            resend_id = ''
            try:
                resend_id = str(json.loads(body).get('id') or '')
            except Exception:
                pass
            logger.info('[EMAIL] Recuperação de senha aceita pelo Resend para %s; status=%s; resend_id=%s', masked, response.status, resend_id or 'n/d')
            return resend_id
    except HTTPError as exc:
        try:
            detail = exc.read().decode('utf-8', errors='replace')
        except Exception:
            detail = str(exc)
        logger.error('[EMAIL] Falha Resend para %s: HTTP %s; resposta=%s', masked, getattr(exc, 'code', 'n/d'), detail[:1500])
        raise EmailDeliveryError(f'Falha no envio do e-mail: HTTP {getattr(exc, "code", "n/d")}') from exc
    except (URLError, TimeoutError) as exc:
        logger.exception('[EMAIL] Falha de conexão com Resend para %s: %s', masked, exc)
        raise EmailDeliveryError(f'Falha de conexão com o serviço de e-mail: {exc}') from exc
    except EmailDeliveryError:
        raise
    except Exception as exc:
        logger.exception('[EMAIL] Erro inesperado ao enviar recuperação para %s', masked)
        raise EmailDeliveryError(f'Erro inesperado no envio: {exc}') from exc
