from html import escape

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import TelegramAPIError

from keyboards.default.menu import contact_keyboard
from keyboards.inline.buttons import subscribe_keyboard, url_button
from loader import dp
from utils import api
from utils.subscription import missing_channels

from .common import REGISTER_TEXT, SERVER_ERROR, menu_for, send_plans

REGISTER_FOR_LOGIN = (
    "👋 <b>ExamBridge'ga xush kelibsiz!</b>\n\n"
    "Saytga kirish uchun avval bir bosishda ro'yxatdan o'ting — pastdagi "
    "<b>📱 Telefon raqamni yuborish</b> tugmasini bosing."
)


def login_keyboard(token, signed_up):
    action = 'new' if signed_up else 'ok'
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton('✅ Ha, kiraman', callback_data=f'login:{action}:{token}'),
        InlineKeyboardButton("❌ Yo'q", callback_data=f'login:no:{token}'),
    )


async def ask_login_confirm(message: types.Message, token, signed_up=False):
    """Saytdagi «Continue with Telegram» so'rovini aniq tasdiqlatamiz."""
    await message.answer(
        "🔐 <b>ExamBridge saytiga kirish</b>\n\n"
        "Saytda «Continue with Telegram» tugmasini hozir o'zingiz bosdingizmi? "
        "Unda tasdiqlang — sayt o'zi ochiladi.\n\n"
        "⚠️ Agar bu havolani sizga boshqa birov yuborgan bo'lsa, <b>bosmang</b>: "
        "u sizning akkauntingizga kirib oladi.",
        reply_markup=login_keyboard(token, signed_up),
    )


async def run_start(message: types.Message, user: types.User, args: str, state: FSMContext):
    """/start mantiqi. user — xabar egasi (tugma bosilganda message.from_user bot bo'ladi)."""
    args = (args or '').strip()

    if args.startswith('login_'):
        try:
            data = await api.sync_user(user)
        except api.ApiError:
            await message.answer(SERVER_ERROR)
            return
        if not data.get('registered'):
            await state.update_data(after_register=args)
            await message.answer(REGISTER_FOR_LOGIN, reply_markup=contact_keyboard())
            return
        await ask_login_confirm(message, args[6:])
        return

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


@dp.callback_query_handler(text_startswith='login:', state='*')
async def login_decision(call: types.CallbackQuery):
    _, action, token = call.data.split(':', 2)

    async def say(text):
        try:
            await call.message.edit_text(text)
        except TelegramAPIError:
            pass

    if action == 'no':
        await call.answer('Bekor qilindi')
        await say("❌ Bekor qilindi. Hech kim akkauntingizga kirmadi.")
        return
    try:
        await api.confirm_login(call.from_user, token, signed_up=action == 'new')
    except api.ApiError as e:
        if e.code == 'bad_token':
            await call.answer('Eskirgan')
            await say(
                "⌛ Bu so'rov eskirgan (5 daqiqa amal qiladi).\n"
                "Saytda «Continue with Telegram» tugmasini qayta bosing."
            )
        elif e.code == 'not_registered':
            await call.answer()
            await call.message.answer(REGISTER_FOR_LOGIN, reply_markup=contact_keyboard())
        else:
            await call.answer(SERVER_ERROR, show_alert=True)
        return
    await call.answer('✅ Tasdiqlandi')
    await say("✅ <b>Tasdiqlandi!</b>\n\nSaytga qayting — kirish avtomatik bo'ladi.")


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
    after = state_data.get('after_register') or ''

    if after.startswith('login_'):
        # Saytdan «Continue with Telegram» orqali kelgan: kirishni tasdiqlatamiz, xolos.
        await message.answer("🎉 <b>Ro'yxatdan o'tdingiz!</b>", reply_markup=menu_for(message.from_user.id))
        await ask_login_confirm(message, after[6:], signed_up=bool(data.get('created')))
        return

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

    if after == 'premium':
        await send_plans(message)
