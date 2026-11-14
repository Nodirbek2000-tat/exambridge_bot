"""
ExamBridge sayti bilan aloqa (/api/bot/...).

Har bir so'rov X-Bot-Secret kaliti bilan boradi; sayt boshqa hech kimga bu
yo'llarni ochmaydi.
"""
import logging

import aiohttp

from data import config

log = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)


class ApiError(Exception):
    def __init__(self, status, code='error', detail=''):
        super().__init__(f'{status} {code}: {detail}')
        self.status = status
        self.code = code
        self.detail = detail


_session = None


def _headers():
    headers = {
        'X-Bot-Secret': config.BOT_API_SECRET,
        'Accept': 'application/json',
        'User-Agent': 'ExamBridgeBot/1.0',
    }
    if config.BACKEND_HOST:
        # The bot talks to Django directly inside Docker, past nginx: tell it
        # which site this is and that the outside connection is HTTPS.
        headers['Host'] = config.BACKEND_HOST
        headers['X-Forwarded-Proto'] = 'https'
    return headers


async def _get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(timeout=TIMEOUT, headers=_headers())
    return _session


async def close():
    if _session is not None and not _session.closed:
        await _session.close()


async def _request(method, path, *, json=None, data=None):
    session = await _get_session()
    url = f'{config.BACKEND_URL}/api/bot/{path}'
    try:
        async with session.request(method, url, json=json, data=data, allow_redirects=False) as res:
            if res.status == 204:
                return {}
            try:
                body = await res.json(content_type=None)
            except Exception:
                body = {}
            if res.status >= 400 or not isinstance(body, dict):
                body = body if isinstance(body, dict) else {}
                raise ApiError(res.status, body.get('code', 'error'), body.get('detail', ''))
            return body
    except ApiError:
        raise
    except Exception as e:
        log.exception('Backend %s %s failed', method, path)
        raise ApiError(0, 'unreachable', str(e))


def _profile(user):
    return {
        'telegram_id': user.id,
        'username': user.username or '',
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
    }


# ── Users ─────────────────────────────────────────────────────────────────────

async def sync_user(user):
    """{'registered': bool, 'account': {...}}"""
    return await _request('POST', 'users/sync/', json=_profile(user))


async def register(user, phone):
    return await _request('POST', 'users/register/', json={**_profile(user), 'phone': phone})


async def link(user, token):
    return await _request('POST', 'users/link/', json={**_profile(user), 'token': token})


async def confirm_login(user, token, signed_up=False):
    """Saytdagi «Continue with Telegram» so'rovini tasdiqlash."""
    return await _request('POST', 'users/login-confirm/', json={
        'telegram_id': user.id, 'token': token, 'signed_up': signed_up,
    })


async def login_link(telegram_id):
    return await _request('POST', 'users/login-link/', json={'telegram_id': telegram_id})


async def pay_check(user, token):
    """Saytdagi «Pay via Telegram»: to'lov qaysi akkaunt uchun ekanini bilish (hech narsa o'zgarmaydi)."""
    return await _request('POST', 'users/pay-check/', json={**_profile(user), 'token': token})


async def pay_confirm(user, token):
    """O'quvchi akkauntni tasdiqladi: keyingi cheklar shu akkauntga yoziladi."""
    return await _request('POST', 'users/pay-confirm/', json={**_profile(user), 'token': token})


# ── Payments ──────────────────────────────────────────────────────────────────

async def plans(telegram_id=None):
    """Tariflar va karta. telegram_id bilan — Premium qaysi akkauntga ochilishi ham (for_account)."""
    return await _request('GET', f'plans/?telegram_id={telegram_id}' if telegram_id else 'plans/')


async def create_payment(telegram_id, plan, content, filename, content_type):
    form = aiohttp.FormData()
    form.add_field('telegram_id', str(telegram_id))
    form.add_field('plan', plan)
    form.add_field('receipt', content, filename=filename, content_type=content_type)
    return await _request('POST', 'payments/', data=form)


def _admin(user):
    return {
        'admin_telegram_id': user.id,
        'admin_name': f'@{user.username}' if user.username else user.full_name,
    }


async def approve(payment_id, admin_user):
    return await _request('POST', f'payments/{payment_id}/approve/', json=_admin(admin_user))


async def reject(payment_id, admin_user, reason):
    return await _request('POST', f'payments/{payment_id}/reject/', json={**_admin(admin_user), 'reason': reason})


# ── Channels and stats ────────────────────────────────────────────────────────

async def channels():
    return (await _request('GET', 'channels/')).get('channels', [])


async def add_channel(chat_id, title, username='', invite_link=''):
    return await _request('POST', 'channels/', json={
        'chat_id': chat_id, 'title': title, 'username': username or '', 'invite_link': invite_link or '',
    })


async def delete_channel(chat_id):
    return await _request('DELETE', f'channels/{chat_id}/')


async def user_ids(audience='all'):
    """/admin xabar tarqatish uchun: {'ids': [...], 'counts': {'all', 'premium', 'free'}}."""
    return await _request('GET', f'users/ids/?audience={audience}')


async def stats():
    return await _request('GET', 'stats/')
