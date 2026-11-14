"""Premium sotib olish: tarif → karta → chek."""
import io
from html import escape

from aiogram import types
from aiogram.dispatcher import FSMContext

from data.config import ADMINS, SUPPORT_USERNAME
from keyboards.default.menu import BTN_CANCEL, BTN_PREMIUM, BTN_PREMIUM_ACTIVE, cancel_keyboard
from keyboards.inline.buttons import decision_keyboard, money, plan_title
from loader import dp
from states.forms import PaymentForm
from utils import api
from utils.misc import rate_limit

from .common import SERVER_ERROR, account_label, account_or_prompt, menu_for, send_plans

MAX_RECEIPT_BYTES = 10 * 1024 * 1024
DOC_TYPES = {
    'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'application/pdf': '.pdf',
}


@dp.message_handler(text=[BTN_PREMIUM, BTN_PREMIUM_ACTIVE])
@dp.message_handler(commands=['premium'])
async def premium_menu(message: types.Message):
    account = await account_or_prompt(message)
    if account is None:
        return
    await send_plans(message, account)


@dp.callback_query_handler(text_startswith='plan:', state='*')
async def choose_plan(call: types.CallbackQuery, state: FSMContext):
    plan_id = call.data.split(':', 1)[1]
    try:
        data = await api.plans()
    except api.ApiError:
        await call.answer(SERVER_ERROR, show_alert=True)
        return
    plan = next((p for p in data.get('plans', []) if p['id'] == plan_id), None)
    if not data.get('accepting') or plan is None:
        await call.answer("Hozircha to'lov qabul qilinmayapti", show_alert=True)
        return
    await call.answer()

    card = data['card']
    holder = escape(card.get('holder') or '')
    label = escape(card.get('label') or '')
    owner = ' · '.join(x for x in (holder, label) if x)
    await state.set_state(PaymentForm.receipt)
    await state.update_data(plan=plan['id'], months=plan['months'], price=plan['price'])
    await call.message.answer(
        f"💳 <b>To'lov: {plan_title(plan['months'])} — {money(plan['price'])} so'm</b>\n\n"
        f"1️⃣ Quyidagi kartaga aynan <b>{money(plan['price'])} so'm</b> o'tkazing:\n\n"
        f"<code>{escape(card['number'])}</code>\n"
        + (f"👤 {owner}\n" if owner else '')
        + "<i>(raqam ustiga bossangiz nusxa olinadi)</i>\n\n"
        "2️⃣ To'lov chekini — <b>skrinshot yoki PDF</b> — shu yerga yuboring.\n\n"
        "⏳ Chek tekshirilgach, Premium avtomatik ochiladi va sizga xabar keladi.",
        reply_markup=cancel_keyboard(),
    )


@dp.message_handler(text=BTN_CANCEL, state=PaymentForm.receipt)
async def cancel_payment(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Bekor qilindi.", reply_markup=menu_for(message.from_user.id))


async def _download(file_obj):
    buf = io.BytesIO()
    await file_obj.download(destination_file=buf)
    return buf.getvalue()


async def _submit(message: types.Message, state: FSMContext, content, filename, content_type):
    data = await state.get_data()
    wait = await message.answer("⏳ Chek yuborilmoqda...")
    try:
        res = await api.create_payment(message.from_user.id, data['plan'], content, filename, content_type)
    except api.ApiError as e:
        await wait.delete()
        if e.code == 'too_many_pending':
            await message.answer(
                "⏳ Sizda tekshiruvni kutayotgan cheklar bor. Ular tekshirilgach, yangisini yuborishingiz mumkin.",
                reply_markup=menu_for(message.from_user.id),
            )
            await state.finish()
        elif e.code == 'closed':
            await message.answer("⏸ Hozircha to'lov qabul qilinmayapti.", reply_markup=menu_for(message.from_user.id))
            await state.finish()
        elif e.code == 'bad_receipt':
            await message.answer("⚠️ Chekni rasm (JPG, PNG) yoki PDF ko'rinishida, 10 MB dan kichik qilib yuboring.")
        elif e.code == 'not_registered':
            await state.finish()
            await account_or_prompt(message)
        else:
            await message.answer(SERVER_ERROR)
        return

    await wait.delete()
    await state.finish()
    await message.answer(
        f"✅ <b>Chekingiz qabul qilindi!</b> (№{res['id']})\n\n"
        f"Tarif: {plan_title(res['months'])} — {money(res['amount'])} so'm\n"
        + (f"👤 Akkaunt: <b>{account_label(res['account'])}</b>\n" if res.get('account') else '')
        + "Admin tekshirgach, Premium shu akkauntda avtomatik ochiladi va sizga shu yerda xabar keladi. "
        "Odatda bu ko'p vaqt olmaydi.\n\n"
        f"Savol bo'lsa: @{SUPPORT_USERNAME}",
        reply_markup=menu_for(message.from_user.id),
    )
    if not res.get('posted'):
        # To'lovlar kanaliga yuborib bo'lmadi (bot u yerda admin emasmi?) — adminlarga to'g'ridan-to'g'ri.
        await _send_to_admins(message, res)


async def _send_to_admins(message: types.Message, res):
    user = message.from_user
    caption = (
        f"🧾 <b>Yangi to'lov #{res['id']}</b> (kanalga yuborilmadi!)\n\n"
        f"👤 {escape(user.full_name)}" + (f" · @{escape(user.username)}" if user.username else '') + "\n"
        f"✈️ ID <code>{user.id}</code>\n"
        f"💎 {plan_title(res['months'])} — {money(res['amount'])} so'm"
    )
    for admin in ADMINS:
        try:
            if message.photo:
                await message.bot.send_photo(admin, message.photo[-1].file_id, caption=caption,
                                             reply_markup=decision_keyboard(res['id']))
            else:
                await message.bot.send_document(admin, message.document.file_id, caption=caption,
                                                reply_markup=decision_keyboard(res['id']))
        except Exception:
            pass


@rate_limit(2, 'receipt')
@dp.message_handler(content_types=types.ContentType.PHOTO, state=PaymentForm.receipt)
async def receipt_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    if photo.file_size and photo.file_size > MAX_RECEIPT_BYTES:
        await message.answer("⚠️ Rasm juda katta. 10 MB dan kichik rasm yuboring.")
        return
    content = await _download(photo)
    await _submit(message, state, content, 'receipt.jpg', 'image/jpeg')


@rate_limit(2, 'receipt')
@dp.message_handler(content_types=types.ContentType.DOCUMENT, state=PaymentForm.receipt)
async def receipt_document(message: types.Message, state: FSMContext):
    doc = message.document
    ext = DOC_TYPES.get(doc.mime_type or '')
    if not ext:
        await message.answer("⚠️ Faqat rasm (JPG, PNG) yoki PDF fayl qabul qilinadi.")
        return
    if doc.file_size and doc.file_size > MAX_RECEIPT_BYTES:
        await message.answer("⚠️ Fayl juda katta. 10 MB dan kichik fayl yuboring.")
        return
    content = await _download(doc)
    await _submit(message, state, content, f'receipt{ext}', doc.mime_type)


@dp.message_handler(state=PaymentForm.receipt, content_types=types.ContentType.ANY)
async def receipt_other(message: types.Message):
    await message.answer(
        "📎 Iltimos, to'lov chekini <b>rasm</b> yoki <b>PDF</b> ko'rinishida yuboring.\n"
        "Bekor qilish uchun <b>❌ Bekor qilish</b> tugmasini bosing.",
        reply_markup=cancel_keyboard(),
    )
