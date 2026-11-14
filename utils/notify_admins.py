import asyncio
import logging

from aiogram import Dispatcher

from data.config import ADMINS

# Sayt qayta ishga tushayotganda (migratsiya, collectstatic) bir-ikki daqiqa javob bermaydi.
RETRIES = 12
RETRY_SECONDS = 10


async def _check_backend():
    from utils import api

    for attempt in range(RETRIES):
        try:
            data = await api.plans()
        except api.ApiError as e:
            if e.status == 0 and attempt < RETRIES - 1:
                await asyncio.sleep(RETRY_SECONDS)      # sayt hali yonmagan — kutamiz
                continue
            if e.status == 403:
                return "❌ Sayt botni tanimadi (403): BOT_API_SECRET saytdagi TELEGRAM_BOT_API_SECRET bilan bir xil emas."
            if e.status == 0:
                return "❌ Saytga ulanib bo'lmadi: sayt (web konteyneri) ishlayaptimi va BACKEND_URL to'g'rimi?"
            return f"❌ Sayt xato qaytardi ({e.status} {e.code})."
        text = "✅ Sayt bilan aloqa bor"
        if not data.get('accepting'):
            text += "\n⚠️ To'lov qabul qilinmayapti: admin panel → Payments da karta raqamini kiriting"
        return text


async def _notify(dp: Dispatcher):
    status = await _check_backend()
    for admin in ADMINS:
        try:
            await dp.bot.send_message(admin, f"🤖 Bot ishga tushdi\n{status}")
        except Exception as err:
            logging.exception(err)


async def on_startup_notify(dp: Dispatcher):
    # Orqa fonda: sayt kutilayotganda ham bot foydalanuvchilarga javob beraveradi.
    asyncio.get_event_loop().create_task(_notify(dp))
