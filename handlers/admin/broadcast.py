"""/admin → 📢 Xabar yuborish: bitta xabarni bot foydalanuvchilariga tarqatish (faqat ADMINS).

Admin istalgan xabar yuboradi (matn, rasm, video, fayl, ovoz), bot uni aynan
o'sha ko'rinishda nusxalaydi. Telegram cheklovi: sekundiga ~30 xabar, shuning
uchun biroz sekinroq yuboriladi va jarayon orqa fonda ketadi.
"""
import asyncio
import logging
import time

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import (
    BotBlocked, BotKicked, CantInitiateConversation, ChatNotFound, RetryAfter, TelegramAPIError, UserDeactivated,
)

from data.config import ADMINS
from keyboards.default.menu import BTN_CANCEL, cancel_keyboard
from loader import dp
from states.forms import AdminForm
from utils import api

log = logging.getLogger(__name__)

SEND_GAP = 0.05          # 20 xabar/sekund — Telegram chegarasidan ancha past
PROGRESS_EVERY = 5       # soniyada bir marta "yuborilmoqda" yangilanadi
GONE = (BotBlocked, BotKicked, CantInitiateConversation, ChatNotFound, UserDeactivated)
AUDIENCES = [('all', '👥 Hammaga'), ('premium', '💎 Faqat Premium'), ('free', '🆓 Premiumsizlar')]

_running = {'active': False}


def _menu(user_id):
    from handlers.users.common import menu_for
    return menu_for(user_id)


@dp.callback_query_handler(text='adm:bcast', state='*')
async def broadcast_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return await call.answer('⛔ Faqat adminlar uchun', show_alert=True)
    if _running['active']:
        return await call.answer('⏳ Hozir boshqa xabar yuborilmoqda. Tugashini kuting.', show_alert=True)
    await call.answer()
    await state.set_state(AdminForm.broadcast)
    await call.message.answer(
        "📢 <b>Xabar yuborish</b>\n\n"
        "Yubormoqchi bo'lgan xabarni shu yerga yuboring: matn, rasm, video, fayl yoki ovozli xabar. "
        "Bot uni aynan shu ko'rinishda yuboradi.\n\n"
        "<i>Albom (bir nechta rasm birga) bitta xabar bo'lib ketmaydi — rasmni bittadan, izohi bilan yuboring.</i>",
        reply_markup=cancel_keyboard(),
    )


@dp.message_handler(text=BTN_CANCEL, state=[AdminForm.broadcast, AdminForm.broadcast_confirm])
async def broadcast_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer('Bekor qilindi.', reply_markup=_menu(message.from_user.id))


@dp.message_handler(state=AdminForm.broadcast, content_types=types.ContentType.ANY)
async def broadcast_got_message(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    if message.is_command():          # /start va boshqa buyruqlar tarqatilmaydi
        await state.finish()
        await message.answer("Xabar yuborish bekor qilindi.", reply_markup=_menu(message.from_user.id))
        return
    try:
        counts = (await api.user_ids('all'))['counts']
    except api.ApiError:
        await message.answer("⚠️ Sayt bilan aloqa yo'q. Birozdan keyin qayta urinib ko'ring.")
        return
    await state.update_data(bc_chat=message.chat.id, bc_message=message.message_id)
    await state.set_state(AdminForm.broadcast_confirm)
    kb = InlineKeyboardMarkup(row_width=1)
    for key, label in AUDIENCES:
        kb.add(InlineKeyboardButton(f'{label} ({counts.get(key, 0)})', callback_data=f'bc:{key}'))
    kb.add(InlineKeyboardButton('❌ Bekor qilish', callback_data='bc:cancel'))
    await message.reply("👆 Xabar shu ko'rinishda boradi.\n\n<b>Kimga yuboramiz?</b>", reply_markup=kb)


@dp.callback_query_handler(text_startswith='bc:', state=AdminForm.broadcast_confirm)
async def broadcast_confirm(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS:
        return await call.answer('⛔ Faqat adminlar uchun', show_alert=True)
    choice = call.data[3:]
    data = await state.get_data()
    await state.finish()

    if choice == 'cancel':
        await call.answer('Bekor qilindi')
        await call.message.edit_text('❌ Bekor qilindi.')
        await call.message.answer('Menyu 👇', reply_markup=_menu(call.from_user.id))
        return
    if _running['active']:
        return await call.answer('⏳ Hozir boshqa xabar yuborilmoqda.', show_alert=True)
    try:
        ids = (await api.user_ids(choice))['ids']
    except api.ApiError:
        return await call.answer("⚠️ Sayt bilan aloqa yo'q", show_alert=True)
    if not ids:
        await call.answer()
        await call.message.edit_text("Bu guruhda hali hech kim yo'q.")
        return

    await call.answer('Yuborish boshlandi')
    progress = await call.message.edit_text(f'⏳ Yuborilmoqda: 0 / {len(ids)}')
    await call.message.answer(
        "Xabar orqa fonda yuborilmoqda — botdan bemalol foydalanaverishingiz mumkin. Tugagach hisobot keladi.",
        reply_markup=_menu(call.from_user.id),
    )
    _running['active'] = True
    asyncio.get_event_loop().create_task(
        _run(call.bot, data['bc_chat'], data['bc_message'], ids, progress),
    )


async def _run(bot, from_chat, message_id, ids, progress):
    sent = gone = failed = 0
    started = last = time.monotonic()
    try:
        for i, user_id in enumerate(ids, 1):
            while True:
                try:
                    await bot.copy_message(user_id, from_chat, message_id)
                    sent += 1
                except RetryAfter as e:
                    await asyncio.sleep(e.timeout + 1)      # Telegram "sekinroq" dedi
                    continue
                except GONE:
                    gone += 1
                except TelegramAPIError as e:
                    failed += 1
                    log.warning('Broadcast to %s failed: %s', user_id, e)
                break
            await asyncio.sleep(SEND_GAP)
            if time.monotonic() - last > PROGRESS_EVERY:
                last = time.monotonic()
                try:
                    await progress.edit_text(f'⏳ Yuborilmoqda: {i} / {len(ids)}')
                except TelegramAPIError:
                    pass
    finally:
        _running['active'] = False

    minutes = max(1, round((time.monotonic() - started) / 60))
    report = (
        "✅ <b>Xabar yuborildi</b>\n\n"
        f"📬 Yetib bordi: <b>{sent}</b>\n"
        f"🚫 Botni bloklagan yoki o'chirilgan: {gone}\n"
        f"⚠️ Boshqa xato: {failed}\n"
        f"👥 Jami: {len(ids)} · ⏱ ~{minutes} daqiqa"
    )
    try:
        await progress.edit_text(report)
    except TelegramAPIError:
        await bot.send_message(progress.chat.id, report)
