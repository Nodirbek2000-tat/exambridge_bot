import logging

from aiogram import Dispatcher

from data.config import ADMINS


async def on_startup_notify(dp: Dispatcher):
    from utils import api

    try:
        data = await api.plans()
        backend = "✅ Sayt bilan aloqa bor"
        if not data.get('accepting'):
            backend += "\n⚠️ To'lov qabul qilinmayapti: admin panel → Payments da karta raqamini kiriting"
    except api.ApiError as e:
        backend = f"❌ Sayt bilan aloqa yo'q ({e.status} {e.code}). BACKEND_URL va BOT_API_SECRET ni tekshiring."

    for admin in ADMINS:
        try:
            await dp.bot.send_message(admin, f"🤖 Bot ishga tushdi\n{backend}")
        except Exception as err:
            logging.exception(err)
