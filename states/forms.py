from aiogram.dispatcher.filters.state import State, StatesGroup


class PaymentForm(StatesGroup):
    receipt = State()      # tarif tanlangan, chek kutilmoqda


class AdminForm(StatesGroup):
    channel = State()      # yangi majburiy kanal kutilmoqda
    broadcast = State()          # tarqatiladigan xabar kutilmoqda
    broadcast_confirm = State()  # kimga yuborish tanlanmoqda
