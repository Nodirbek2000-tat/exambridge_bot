from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandHelp

from data.config import SITE_URL, SUPPORT_USERNAME
from keyboards.default.menu import BTN_ACCOUNT, BTN_HELP, BTN_SITE
from keyboards.inline.buttons import url_button
from loader import dp
from utils import api

from .common import SERVER_ERROR, account_or_prompt, account_text, menu_for


@dp.message_handler(text=BTN_SITE)
@dp.message_handler(commands=['site'])
async def site_login(message: types.Message):
    if await account_or_prompt(message) is None:
        return
    try:
        link = await api.login_link(message.from_user.id)
    except api.ApiError:
        await message.answer(SERVER_ERROR)
        return
    await message.answer(
        "🌐 Saytga parolsiz kirish uchun bosing.\n"
        "<i>Havola 10 daqiqa va faqat bir marta ishlaydi — uni hech kimga yubormang.</i>",
        reply_markup=url_button('🌐 ExamBridge saytiga kirish', link['url']),
    )


@dp.message_handler(text=BTN_ACCOUNT)
async def my_account(message: types.Message):
    account = await account_or_prompt(message)
    if account is None:
        return
    await message.answer(account_text(account), reply_markup=menu_for(message.from_user.id))


@dp.message_handler(text=BTN_HELP)
@dp.message_handler(CommandHelp())
async def help_text(message: types.Message):
    await message.answer(
        "☎️ <b>Yordam</b>\n\n"
        f"Savol va muammolar bo'yicha: @{SUPPORT_USERNAME}\n"
        f"Sayt: {SITE_URL}\n"
        f"To'lovni qaytarish shartlari: {SITE_URL}/refund-policy?lang=uz\n\n"
        "Buyruqlar:\n"
        "/start — botni qayta ishga tushirish\n"
        "/premium — Premium sotib olish\n"
        "/site — saytga kirish havolasi",
        reply_markup=menu_for(message.from_user.id),
        disable_web_page_preview=True,
    )


@dp.message_handler(content_types=types.ContentType.ANY)
async def fallback(message: types.Message):
    """Boshqa hamma narsa: ro'yxatdan o'tmagan bo'lsa raqam so'raymiz, aks holda menyu."""
    if message.chat.type != types.ChatType.PRIVATE:
        return
    if await account_or_prompt(message) is None:
        return
    await message.answer("Kerakli bo'limni pastdagi menyudan tanlang 👇", reply_markup=menu_for(message.from_user.id))
