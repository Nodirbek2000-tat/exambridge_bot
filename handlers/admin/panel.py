"""/admin: sayt statistikasi va majburiy kanallar (faqat ADMINS)."""
import re
from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import TelegramAPIError

from data.config import ADMINS
from keyboards.default.menu import BTN_ADMIN, BTN_CANCEL, cancel_keyboard
from keyboards.inline.buttons import admin_keyboard, channels_keyboard, money
from loader import dp
from states.forms import AdminForm
from utils import api, subscription

TASHKENT = timezone(timedelta(hours=5))
SERVER_ERROR = "⚠️ Sayt bilan aloqa yo'q. Birozdan keyin qayta urinib ko'ring."


def n(value):
    return f'{int(value or 0):,}'.replace(',', ' ')


def stats_text(s):
    u, b, m, p = s['users'], s['bot'], s['mocks'], s['payments']
    now = datetime.now(TASHKENT).strftime('%d.%m.%Y %H:%M')
    return (
        f"📊 <b>ExamBridge statistikasi</b>\n🕒 {now}\n\n"
        "👥 <b>Foydalanuvchilar</b>\n"
        f"• Jami: <b>{n(u['total'])}</b>\n"
        f"• Bugun: +{n(u['today'])} · 7 kunda: +{n(u['week'])}\n"
        f"• Hozir onlayn: <b>{n(u['online'])}</b>\n"
        f"• Bugun saytga kirgan: {n(u['active_today'])}\n"
        f"• Premium: {n(u['premium'])}\n\n"
        "🤖 <b>Bot</b>\n"
        f"• Bot foydalanuvchilari: {n(b['total'])} (bugun +{n(b['today'])})\n"
        f"• Bot orqali ro'yxatdan o'tgan: {n(b['registered_here'])}\n\n"
        "📝 <b>Mock testlar</b>\n"
        f"• Bugun boshlangan: {n(m['started_today'])}\n"
        f"• Bugun tugatilgan: {n(m['completed_today'])} · 7 kunda: {n(m['completed_week'])}\n\n"
        "💳 <b>To'lovlar</b>\n"
        f"• Tekshiruv kutmoqda: <b>{n(p['pending'])}</b>\n"
        f"• Bugun: {n(p['today_count'])} ta — {money(p['today_sum'])} so'm\n"
        f"• Shu oy: {n(p['month_count'])} ta — {money(p['month_sum'])} so'm\n"
        f"• Jami tushum: {money(p['total_sum'])} so'm"
    )


def admin_only(user_id):
    return user_id in ADMINS


@dp.message_handler(commands=['admin'], state='*')
@dp.message_handler(text=BTN_ADMIN, state='*')
async def admin_panel(message: types.Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    await state.finish()
    try:
        s = await api.stats()
    except api.ApiError:
        await message.answer(SERVER_ERROR)
        return
    await message.answer(stats_text(s), reply_markup=admin_keyboard())


@dp.callback_query_handler(text='adm:stats', state='*')
async def admin_stats(call: types.CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer('⛔ Faqat adminlar uchun', show_alert=True)
    await state.finish()
    try:
        s = await api.stats()
    except api.ApiError:
        return await call.answer(SERVER_ERROR, show_alert=True)
    await call.answer('Yangilandi')
    try:
        await call.message.edit_text(stats_text(s), reply_markup=admin_keyboard())
    except TelegramAPIError:
        pass        # matn o'zgarmagan


async def _show_channels(message: types.Message, edit=True):
    try:
        items = await subscription.channels(force=True)
    except api.ApiError:
        items = []
    if items:
        rows = '\n'.join(f"• <a href=\"{escape(c['url'])}\">{escape(c['title'])}</a>" for c in items)
        text = f"📢 <b>Majburiy kanallar</b> ({len(items)})\n\n{rows}\n\nO'chirish uchun kanal nomini bosing."
    else:
        text = "📢 <b>Majburiy kanallar</b>\n\nHozircha kanal yo'q — bot hammaga ochiq."
    kb = channels_keyboard(items)
    if edit:
        try:
            await message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
            return
        except TelegramAPIError:
            pass
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)


@dp.callback_query_handler(text='adm:channels', state='*')
async def admin_channels(call: types.CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer('⛔ Faqat adminlar uchun', show_alert=True)
    await state.finish()
    await call.answer()
    await _show_channels(call.message)


@dp.callback_query_handler(text_startswith='adm:chdel:', state='*')
async def admin_channel_delete(call: types.CallbackQuery):
    if not admin_only(call.from_user.id):
        return await call.answer('⛔ Faqat adminlar uchun', show_alert=True)
    chat_id = call.data.rsplit(':', 1)[1]
    try:
        await api.delete_channel(chat_id)
    except api.ApiError as e:
        if e.status != 404:
            return await call.answer(SERVER_ERROR, show_alert=True)
    subscription.forget()
    await call.answer("🗑 Kanal o'chirildi")
    await _show_channels(call.message)


@dp.callback_query_handler(text='adm:chadd', state='*')
async def admin_channel_add(call: types.CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer('⛔ Faqat adminlar uchun', show_alert=True)
    await call.answer()
    await state.set_state(AdminForm.channel)
    me = await call.bot.get_me()
    await call.message.answer(
        "➕ <b>Majburiy kanal qo'shish</b>\n\n"
        f"1️⃣ Avval botni (@{me.username}) kanalga <b>admin</b> qiling.\n"
        "2️⃣ Keyin shu yerga yuboring:\n"
        "• kanal <b>@username</b> i (masalan @exambridge_uz), yoki\n"
        "• kanaldagi istalgan postni <b>forward</b> qiling (yopiq kanal uchun), yoki\n"
        "• kanal ID si (-100...).",
        reply_markup=cancel_keyboard(),
    )


@dp.message_handler(text=BTN_CANCEL, state=AdminForm.channel)
async def admin_channel_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    from handlers.users.common import menu_for
    await message.answer('Bekor qilindi.', reply_markup=menu_for(message.from_user.id))


def _channel_ref(message: types.Message):
    """Xabardan kanal manzilini oladi: forward, @username, t.me/link yoki -100 id."""
    if message.forward_from_chat and message.forward_from_chat.type == types.ChatType.CHANNEL:
        return message.forward_from_chat.id
    text = (message.text or '').strip()
    if re.fullmatch(r'-100\d{5,}', text):
        return int(text)
    m = re.fullmatch(r'(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{4,})/?', text)
    if m:
        return '@' + m.group(1)
    if re.fullmatch(r'@?[A-Za-z][A-Za-z0-9_]{3,}', text):
        return '@' + text.lstrip('@')
    return None


@dp.message_handler(state=AdminForm.channel, content_types=types.ContentType.ANY)
async def admin_channel_receive(message: types.Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    ref = _channel_ref(message)
    if ref is None:
        await message.answer(
            "Kanalni aniqlay olmadim. @username, kanal ID si yoki kanaldan forward qilingan post yuboring.",
        )
        return

    bot = message.bot
    try:
        chat = await bot.get_chat(ref)
    except TelegramAPIError:
        await message.answer(
            "❌ <b>Bot bu kanalda admin emas</b> yoki kanal topilmadi.\n"
            "Avval botni kanalga admin qiling, keyin qayta yuboring.",
        )
        return
    if chat.type not in (types.ChatType.CHANNEL, types.ChatType.SUPERGROUP):
        await message.answer("Bu kanal emas. Kanal manzilini yuboring.")
        return

    me = await bot.get_me()
    try:
        member = await bot.get_chat_member(chat.id, me.id)
        is_admin = member.status in ('administrator', 'creator')
    except TelegramAPIError:
        is_admin = False
    if not is_admin:
        await message.answer(
            f"❌ <b>Bot «{escape(chat.title or '')}» kanalida admin emas!</b>\n\n"
            "A'zolikni tekshirish uchun bot kanalda admin bo'lishi shart. "
            f"Kanal sozlamalari → Administratorlar → @{me.username} ni qo'shing, keyin qayta yuboring.",
        )
        return

    invite_link = ''
    if not chat.username:
        invite_link = chat.invite_link or ''
        if not invite_link:
            try:
                invite_link = await bot.export_chat_invite_link(chat.id)
            except TelegramAPIError:
                await message.answer(
                    "❌ Yopiq kanal uchun taklif havolasini ololmadim. "
                    "Botga «Foydalanuvchilarni taklif qilish» huquqini bering va qayta yuboring.",
                )
                return

    try:
        await api.add_channel(chat.id, chat.title or str(chat.id), chat.username or '', invite_link)
    except api.ApiError:
        await message.answer(SERVER_ERROR)
        return

    subscription.forget()
    await state.finish()
    from handlers.users.common import menu_for
    await message.answer(
        f"✅ <b>{escape(chat.title or '')}</b> majburiy kanallarga qo'shildi.",
        reply_markup=menu_for(message.from_user.id),
    )
    await _show_channels(message, edit=False)
