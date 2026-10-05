import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from app.core.config import settings

class EmailDeliveryError(RuntimeError):
    pass

def send_password_reset_email(to_email: str, reset_url: str) -> None:
    if not settings.resend_api_key:
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
    req=Request('https://api.resend.com/emails', data=json.dumps(payload).encode(), method='POST', headers={
        'Authorization': f'Bearer {settings.resend_api_key}', 'Content-Type':'application/json'
    })
    try:
        with urlopen(req, timeout=15) as response:
            if response.status >= 300:
                raise EmailDeliveryError(f'Falha no envio: HTTP {response.status}')
    except (HTTPError, URLError, TimeoutError) as exc:
        raise EmailDeliveryError(f'Falha no envio do e-mail: {exc}') from exc
