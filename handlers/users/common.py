"""Foydalanuvchi bo'limlari uchun umumiy yordamchilar."""
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


def menu_for(user_id):
    return main_menu(is_admin=is_admin(user_id))


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
    return data['account']


def account_text(account):
    lines = ["👤 <b>Hisobim</b>", ""]
    lines.append(f"Ism: {escape(account.get('full_name') or '—')}")
    if account.get('email'):
        lines.append(f"Email: {escape(account['email'])}")
    if account.get('phone'):
        lines.append(f"Telefon: {escape(account['phone'])}")
    if account.get('is_premium'):
        until = account.get('premium_until')
        until = f"{until[8:10]}.{until[5:7]}.{until[0:4]}" if until else 'muddatsiz'
        lines.append(f"Tarif: 💎 <b>Premium</b> — {until} gacha")
    else:
        lines.append("Tarif: Bepul")
    return '\n'.join(lines)


async def send_plans(message: types.Message):
    """Tariflar ro'yxati va tanlash tugmalari."""
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
    text = (
        "💎 <b>ExamBridge Premium</b>\n\n"
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
