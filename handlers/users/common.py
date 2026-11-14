"""Foydalanuvchi bo'limlari uchun umumiy yordamchilar."""
import math
from datetime import datetime
from html import escape

from aiogram import types

from data.config import ADMINS, SITE_URL, SUPPORT_USERNAME
from keyboards.default.menu import contact_keyboard, main_menu
from keyboards.inline.buttons import money, plan_title, plans_keyboard
from utils import api

SERVER_ERROR = "⚠️ Sayt bilan aloqa vaqtincha yo'q. Birozdan keyin qayta urinib ko'ring."

REGISTER_TEXT = (
    "👋 <b>ExamBridge botiga xush kelibsiz!</b>\n\n"
    "Bu yerda siz:\n"
    "• bir bosishda ro'yxatdan o'tasiz,\n"
    "• Premium tarifni karta orqali sotib olasiz,\n"
    "• saytga parolsiz kirasiz.\n\n"
    "Ro'yxatdan o'tish uchun pastdagi <b>📱 Telefon raqamni yuborish</b> tugmasini bosing.\n\n"
    "<i>Saytda allaqachon akkauntingiz bormi? Saytga kiring → Premium → "
    "<b>Pay via Telegram</b> tugmasini bosing — bot o'sha akkauntga ulanadi.</i>"
)


def is_admin(user_id):
    return user_id in ADMINS


# Saytdan kelgan oxirgi akkaunt ma'lumoti (telegram_id -> account). Menyuda Premium
# holatini ko'rsatish uchun; har bir sync bilan yangilanadi.
_accounts = {}


def remember(account):
    if account and account.get('telegram_id'):
        _accounts[account['telegram_id']] = account
    return account


def menu_for(user_id):
    account = _accounts.get(user_id)
    return main_menu(is_admin=is_admin(user_id), premium=bool(account and account.get('is_premium')))


def premium_until_text(account):
    """'13.12.2026 gacha (29 kun qoldi)' yoki 'muddatsiz'."""
    iso = account.get('premium_until')
    if not iso:
        return 'muddatsiz'
    try:
        until = datetime.fromisoformat(iso)
    except ValueError:
        return iso[:10]
    days = max(0, math.ceil((until - datetime.now(until.tzinfo)).total_seconds() / 86400))
    return f"{until:%d.%m.%Y} gacha ({days} kun qoldi)"


async def account_or_prompt(message: types.Message):
    """Ro'yxatdan o'tgan bo'lsa akkaunt ma'lumoti, aks holda raqam so'raydi va None."""
    try:
        data = await api.sync_user(message.from_user)
    except api.ApiError:
        await message.answer(SERVER_ERROR)
        return None
    if not data.get('registered'):
        await message.answer(REGISTER_TEXT, reply_markup=contact_keyboard())
        return None
    return remember(data['account'])


def account_text(account):
    lines = ["👤 <b>Hisobim</b>", ""]
    lines.append(f"Ism: {escape(account.get('full_name') or '—')}")
    if account.get('email'):
        lines.append(f"Email: {escape(account['email'])}")
    if account.get('phone'):
        lines.append(f"Telefon: {escape(account['phone'])}")
    if account.get('is_premium'):
        lines.append(f"Tarif: 💎 <b>Premium</b> — {premium_until_text(account)}")
    else:
        lines.append("Tarif: Bepul")
    return '\n'.join(lines)


async def send_plans(message: types.Message, account=None):
    """Tariflar ro'yxati va tanlash tugmalari. Premium bo'lsa — avval uning holati."""
    account = account or _accounts.get(message.chat.id)
    if account and account.get('is_premium') and not account.get('premium_until'):
        await message.answer(
            "✅ <b>Sizda muddatsiz Premium bor</b> — hamma narsa ochiq, to'lov shart emas.",
            reply_markup=menu_for(message.chat.id),
        )
        return
    try:
        data = await api.plans()
    except api.ApiError:
        await message.answer(SERVER_ERROR)
        return
    if not data.get('accepting'):
        await message.answer(
            "⏸ Hozircha to'lov qabul qilinmayapti. Birozdan keyin qayta urinib ko'ring "
            f"yoki yordamga yozing: @{SUPPORT_USERNAME}"
        )
        return
    plans = data['plans']
    rows = '\n'.join(f"• <b>{plan_title(p['months'])}</b> — {money(p['price'])} so'm" for p in plans)
    if account and account.get('is_premium'):
        header = (
            f"✅ <b>Sizda Premium faol</b> — {premium_until_text(account)}.\n\n"
            "Muddatni uzaytirish uchun tarif tanlang — yangi kunlar hozirgisining ustiga qo'shiladi.\n\n"
        )
    else:
        header = ""
    text = (
        header
        + "💎 <b>ExamBridge Premium</b>\n\n"
        "Premium bilan ochiladi:\n"
        "• barcha IELTS, CEFR va SAT premium mock testlari\n"
        "• Speaking va Writing — AI band bahosi bilan\n"
        "• haqiqiy formatdagi to'liq mock imtihonlar\n"
        "• premium maqolalar va Speaking o'yinining barcha darajalari\n\n"
        "Obuna emas — muddat tugagach, o'zi yechilmaydi.\n\n"
        f"{rows}\n\n"
        "Tarifni tanlang 👇\n\n"
        f"<i>Har qanday to'lov 24 soat ichida qaytariladi. Batafsil: {SITE_URL}/refund-policy?lang=uz</i>"
    )
    await message.answer(text, reply_markup=plans_keyboard(plans), disable_web_page_preview=True)
