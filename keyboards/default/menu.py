from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_PREMIUM = "💎 Premium sotib olish"
BTN_PREMIUM_ACTIVE = "💎 Premium (faol)"
BTN_SITE = "🌐 Saytga kirish"
BTN_ACCOUNT = "👤 Hisobim"
BTN_HELP = "☎️ Yordam"
BTN_ADMIN = "⚙️ Admin panel"
BTN_CANCEL = "❌ Bekor qilish"
BTN_CONTACT = "📱 Telefon raqamni yuborish"


def main_menu(is_admin=False, premium=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(BTN_PREMIUM_ACTIVE if premium else BTN_PREMIUM))
    kb.row(KeyboardButton(BTN_SITE), KeyboardButton(BTN_ACCOUNT))
    kb.row(KeyboardButton(BTN_HELP))
    if is_admin:
        kb.row(KeyboardButton(BTN_ADMIN))
    return kb


def contact_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.row(KeyboardButton(BTN_CONTACT, request_contact=True))
    return kb


def cancel_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(BTN_CANCEL))
    return kb
