from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Saytdagi pricing/card.py REJECT_REASONS kalitlari bilan bir xil.
REJECT_REASONS = [
    ('unreadable', "🧾 Chek o'qilmaydi"),
    ('amount', '💰 Summa mos emas'),
    ('not_received', "🚫 Pul tushmagan"),
    ('duplicate', '♻️ Takroriy chek'),
    ('other', '❔ Boshqa sabab'),
]


def money(amount):
    return f'{int(amount):,}'.replace(',', ' ')


def plan_title(months):
    return f'{months} oy'


def subscribe_keyboard(channels):
    kb = InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        kb.add(InlineKeyboardButton(f"➕ {ch['title']}", url=ch['url']))
    kb.add(InlineKeyboardButton("✅ Obunani tekshirish", callback_data='subs:check'))
    return kb


def plans_keyboard(plans):
    kb = InlineKeyboardMarkup(row_width=1)
    for p in plans:
        kb.add(InlineKeyboardButton(
            f"💎 {plan_title(p['months'])} — {money(p['price'])} so'm",
            callback_data=f"plan:{p['id']}",
        ))
    return kb


def url_button(text, url):
    return InlineKeyboardMarkup().add(InlineKeyboardButton(text, url=url))


def decision_keyboard(payment_id):
    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton('✅ Tasdiqlash', callback_data=f'pay:ok:{payment_id}'),
        InlineKeyboardButton('❌ Rad etish', callback_data=f'pay:no:{payment_id}'),
    )


def reject_reasons_keyboard(payment_id):
    kb = InlineKeyboardMarkup(row_width=1)
    for code, label in REJECT_REASONS:
        kb.add(InlineKeyboardButton(label, callback_data=f'pay:rs:{payment_id}:{code}'))
    kb.add(InlineKeyboardButton('⬅️ Orqaga', callback_data=f'pay:back:{payment_id}'))
    return kb


def admin_keyboard():
    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton('🔄 Yangilash', callback_data='adm:stats'),
        InlineKeyboardButton('📢 Xabar yuborish', callback_data='adm:bcast'),
        InlineKeyboardButton('📌 Majburiy kanallar', callback_data='adm:channels'),
    )


def channels_keyboard(channels):
    kb = InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        kb.add(InlineKeyboardButton(f"🗑 {ch['title']}", callback_data=f"adm:chdel:{ch['chat_id']}"))
    kb.add(InlineKeyboardButton("➕ Kanal qo'shish", callback_data='adm:chadd'))
    kb.add(InlineKeyboardButton('⬅️ Statistika', callback_data='adm:stats'))
    return kb
