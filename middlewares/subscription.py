from aiogram import Dispatcher, types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

from keyboards.inline.buttons import subscribe_keyboard
from utils.subscription import missing_channels

SUBSCRIBE_TEXT = (
    "📢 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling.\n\n"
    "A'zo bo'lgach, <b>✅ Obunani tekshirish</b> tugmasini bosing."
)


class SubscriptionMiddleware(BaseMiddleware):
    """Majburiy kanallarga a'zo bo'lmagan foydalanuvchini to'xtatadi (faqat shaxsiy chat)."""

    async def on_pre_process_message(self, message: types.Message, data: dict):
        if message.chat.type != types.ChatType.PRIVATE:
            return
        missing = await missing_channels(message.bot, message.from_user.id)
        if not missing:
            return
        # /start link_... yoki /start premium bo'lsa, a'zo bo'lgandan keyin davom etamiz.
        if message.is_command() and message.get_command(pure=True) == 'start':
            state = Dispatcher.get_current().current_state(chat=message.chat.id, user=message.from_user.id)
            await state.update_data(pending_start=message.get_args() or '')
        await message.answer(SUBSCRIBE_TEXT, reply_markup=subscribe_keyboard(missing))
        raise CancelHandler()

    async def on_pre_process_callback_query(self, call: types.CallbackQuery, data: dict):
        # Kanal ichidagi tugmalar (to'lovni tasdiqlash) va tekshirish tugmasining o'zi o'tadi.
        if call.message is None or call.message.chat.type != types.ChatType.PRIVATE:
            return
        if call.data == 'subs:check':
            return
        missing = await missing_channels(call.bot, call.from_user.id)
        if not missing:
            return
        await call.answer("Avval kanallarga a'zo bo'ling", show_alert=True)
        await call.message.answer(SUBSCRIBE_TEXT, reply_markup=subscribe_keyboard(missing))
        raise CancelHandler()
