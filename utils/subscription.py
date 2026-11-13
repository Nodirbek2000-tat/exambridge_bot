"""
Majburiy kanallar: foydalanuvchi hammasiga a'zo bo'lmaguncha bot ishlamaydi.

Kanallar ro'yxati saytda saqlanadi (admin /admin → Majburiy kanallar orqali
qo'shadi). A'zolikni tekshirish uchun bot har bir kanalda admin bo'lishi kerak.
"""
import logging
import time

from aiogram.utils.exceptions import TelegramAPIError

from data.config import ADMINS
from utils import api

log = logging.getLogger(__name__)

CHANNELS_TTL = 60          # kanallar ro'yxati shuncha soniya keshda turadi
MEMBER_TTL = 300           # a'zo ekani tasdiqlangan foydalanuvchi qayta tekshirilmaydi
WARN_EVERY = 3600          # "bot admin emas" ogohlantirishi soatiga bir marta

_channels = {'at': 0.0, 'items': []}
_members = {}               # user_id -> tasdiqlangan vaqt
_warned = {}                # chat_id -> oxirgi ogohlantirish vaqti

JOINED = {'creator', 'administrator', 'member'}


async def channels(force=False):
    now = time.monotonic()
    if force or now - _channels['at'] > CHANNELS_TTL:
        try:
            _channels['items'] = await api.channels()
            _channels['at'] = now
        except api.ApiError:
            log.warning('Could not load the mandatory channels; using the last list')
    return _channels['items']


def forget():
    """Kanallar o'zgarganda keshni tozalash."""
    _channels['at'] = 0.0
    _members.clear()


async def _warn_admins(bot, channel, reason):
    now = time.monotonic()
    if now - _warned.get(channel['chat_id'], -WARN_EVERY) < WARN_EVERY:
        return
    _warned[channel['chat_id']] = now
    for admin in ADMINS:
        try:
            await bot.send_message(
                admin,
                f"⚠️ <b>{channel['title']}</b> kanalida a'zolikni tekshirib bo'lmadi: {reason}\n"
                "Bot shu kanalda admin ekanini tekshiring. Tuzatilmaguncha bu kanal majburiy emas.",
            )
        except TelegramAPIError:
            pass


async def missing_channels(bot, user_id):
    """Foydalanuvchi hali a'zo bo'lmagan kanallar."""
    if user_id in ADMINS:
        return []
    if time.monotonic() - _members.get(user_id, -MEMBER_TTL) < MEMBER_TTL:
        return []

    missing = []
    for channel in await channels():
        try:
            member = await bot.get_chat_member(channel['chat_id'], user_id)
        except TelegramAPIError as e:
            # Bot kanaldan chiqarilgan yoki admin emas: foydalanuvchini bloklamaymiz.
            log.warning('Cannot check %s: %s', channel['chat_id'], e)
            await _warn_admins(bot, channel, str(e))
            continue
        joined = member.status in JOINED or (member.status == 'restricted' and getattr(member, 'is_member', False))
        if not joined:
            missing.append(channel)

    if not missing:
        _members[user_id] = time.monotonic()
    return missing
