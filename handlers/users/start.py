from html import escape

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart

from keyboards.default.menu import contact_keyboard
from keyboards.inline.buttons import subscribe_keyboard, url_button
from loader import dp
from utils import api
from utils.subscription import missing_channels

from .common import REGISTER_TEXT, SERVER_ERROR, menu_for, send_plans


async def run_start(message: types.Message, user: types.User, args: str, state: FSMContext):
    """/start mantiqi. user — xabar egasi (tugma bosilganda message.from_user bot bo'ladi)."""
    args = (args or '').strip()

    if args.startswith('link_'):
        try:
            data = await api.link(user, args[5:])
        except api.ApiError as e:
            if e.code == 'bad_token':
                await message.answer(
                    "⌛ Bu havola eskirgan yoki allaqachon ishlatilgan.\n"
                    "Saytga qaytib, <b>Pay via Telegram</b> tugmasini qayta bosing."
                )
            elif e.code == 'telegram_taken':
                await message.answer(
                    "⚠️ Bu Telegram boshqa ExamBridge akkauntiga ulangan.\n"
                    "Agar bu xato bo'lsa, ☎️ Yordam orqali bizga yozing."
                )
            else:
                await message.answer(SERVER_ERROR)
                return
        else:
            who = data['account'].get('email') or data['account'].get('full_name')
            await message.answer(
                f"✅ Telegram saytdagi <b>{escape(who or '')}</b> akkauntiga ulandi.",
                reply_markup=menu_for(user.id),
            )
            await send_plans(message)
            return

    try:
        data = await api.sync_user(user)
    except api.ApiError:
        await message.answer(SERVER_ERROR)
        return

    if not data.get('registered'):
        await state.update_data(after_register='premium' if args == 'premium' else '')
        await message.answer(REGISTER_TEXT, reply_markup=contact_keyboard())
        return

    name = escape(user.first_name or data['account'].get('full_name') or '')
    await message.answer(
        f"👋 Xush kelibsiz, <b>{name}</b>!\nKerakli bo'limni tanlang 👇",
        reply_markup=menu_for(user.id),
    )
    if args == 'premium':
        await send_plans(message)


@dp.message_handler(CommandStart(), state='*')
async def bot_start(message: types.Message, state: FSMContext):
    await state.finish()            # /start har qanday boshlangan jarayonni bekor qiladi
    await run_start(message, message.from_user, message.get_args(), state)


@dp.callback_query_handler(text='subs:check', state='*')
async def check_subscription(call: types.CallbackQuery, state: FSMContext):
    missing = await missing_channels(call.bot, call.from_user.id)
    if missing:
        await call.answer("Hali hamma kanallarga a'zo bo'lmadingiz", show_alert=True)
        try:
            await call.message.edit_reply_markup(subscribe_keyboard(missing))
        except Exception:
            pass
        return
    await call.answer("✅ Rahmat!")
    try:
        await call.message.delete()
    except Exception:
        pass
    data = await state.get_data()
    await state.update_data(pending_start='')
    await run_start(call.message, call.from_user, data.get('pending_start', ''), state)


@dp.message_handler(content_types=types.ContentType.CONTACT, state='*')
async def got_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer(
            "Iltimos, o'zingizning raqamingizni pastdagi tugma orqali yuboring 👇",
            reply_markup=contact_keyboard(),
        )
        return
    try:
        data = await api.register(message.from_user, contact.phone_number)
    except api.ApiError:
        await message.answer(SERVER_ERROR)
        return

    state_data = await state.get_data()
    await state.finish()

    if data.get('created'):
        await message.answer(
            "🎉 <b>Ro'yxatdan o'tdingiz!</b>\n\n"
            "Endi saytda mock testlarni yechishingiz mumkin. Saytga kirish uchun "
            "<b>🌐 Saytga kirish</b> tugmasini bosing — parol kerak emas.",
            reply_markup=menu_for(message.from_user.id),
        )
        try:
            link = await api.login_link(message.from_user.id)
            await message.answer(
                "Saytni ochish uchun bosing (havola 10 daqiqa amal qiladi):",
                reply_markup=url_button('🌐 ExamBridge saytiga kirish', link['url']),
            )
        except api.ApiError:
            pass
    else:
        await message.answer("✅ Siz allaqachon ro'yxatdan o'tgansiz.", reply_markup=menu_for(message.from_user.id))

    if state_data.get('after_register') == 'premium':
        await send_plans(message)
