import logging

from aiogram import types

from data.config import ADMINS

USER_COMMANDS = [
    types.BotCommand("start", "Botni ishga tushirish"),
    types.BotCommand("premium", "Premium sotib olish"),
    types.BotCommand("site", "Saytga kirish"),
    types.BotCommand("help", "Yordam"),
]


async def set_default_commands(dp):
    await dp.bot.set_my_commands(USER_COMMANDS)
    # /admin faqat adminlarning menyusida ko'rinadi.
    for admin in ADMINS:
        try:
            await dp.bot.set_my_commands(
                USER_COMMANDS + [types.BotCommand("admin", "Statistika va kanallar")],
                scope=types.BotCommandScopeChat(admin),
            )
        except Exception as err:
            logging.warning("Could not set admin commands for %s: %s", admin, err)
