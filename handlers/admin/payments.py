"""To'lovlar kanalidagi ✅ / ❌ tugmalari. Faqat ADMINS bosa oladi.

Tasdiqlangandan keyin sayt o'zi kanal postini yangilaydi va o'quvchiga xabar
yuboradi, shuning uchun bu yerda faqat qaror saytga uzatiladi.
"""
from aiogram import types
from aiogram.utils.exceptions import TelegramAPIError

from data.config import ADMINS
from keyboards.inline.buttons import decision_keyboard, reject_reasons_keyboard
from loader import dp
from utils import api


def _payment_id(data, index=2):
    try:
        return int(data.split(':')[index])
    except (IndexError, ValueError):
        return None


async def _refuse(call):
    await call.answer('⛔ Faqat adminlar to\'lovni tasdiqlay oladi', show_alert=True)


async def _decided(call, e):
    if e.code == 'already_decided':
        await call.answer("Bu to'lov allaqachon ko'rib chiqilgan", show_alert=True)
        try:
            await call.message.edit_reply_markup(None)
        except TelegramAPIError:
            pass
    elif e.code == 'not_found':
        await call.answer("To'lov topilmadi", show_alert=True)
    else:
        await call.answer("⚠️ Sayt bilan aloqa yo'q, qayta urinib ko'ring", show_alert=True)


@dp.callback_query_handler(text_startswith='pay:ok:', state='*')
async def approve(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return await _refuse(call)
    pid = _payment_id(call.data)
    try:
        res = await api.approve(pid, call.from_user)
    except api.ApiError as e:
        return await _decided(call, e)
    until = res.get('premium_until')
    until = f"{until[8:10]}.{until[5:7]}.{until[0:4]}" if until else 'muddatsiz'
    await call.answer(f'✅ Tasdiqlandi. Premium: {until} gacha')
    if call.message.chat.type == types.ChatType.PRIVATE:
        # Kanalga yuborilmagan zaxira nusxa: tugmalarni shu yerning o'zida olib tashlaymiz.
        try:
            await call.message.edit_caption((call.message.caption or '') + f'\n\n✅ Tasdiqlandi — {until} gacha')
        except TelegramAPIError:
            pass


@dp.callback_query_handler(text_startswith='pay:no:', state='*')
async def ask_reason(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return await _refuse(call)
    await call.answer('Sababni tanlang')
    await call.message.edit_reply_markup(reject_reasons_keyboard(_payment_id(call.data)))


@dp.callback_query_handler(text_startswith='pay:back:', state='*')
async def back(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return await _refuse(call)
    await call.answer()
    await call.message.edit_reply_markup(decision_keyboard(_payment_id(call.data)))


@dp.callback_query_handler(text_startswith='pay:rs:', state='*')
async def reject(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS:
        return await _refuse(call)
    parts = call.data.split(':')
    pid = _payment_id(call.data)
    reason = parts[3] if len(parts) > 3 else 'other'
    try:
        await api.reject(pid, call.from_user, reason)
    except api.ApiError as e:
        return await _decided(call, e)
    await call.answer('❌ Rad etildi. O\'quvchiga xabar yuborildi.')
    if call.message.chat.type == types.ChatType.PRIVATE:
        try:
            await call.message.edit_caption((call.message.caption or '') + '\n\n❌ Rad etildi')
        except TelegramAPIError:
            pass
