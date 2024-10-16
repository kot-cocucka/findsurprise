import logging
import random
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import get_settings

settings = get_settings()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

header_length =  30

header = 'Игра "Нажми на коробку"'
header.rjust(header_length, ' ')


def __(text: str) -> str:
    if len(text) > header_length:
        return text[:header_length - 3] + '...'
    return text.rjust(header_length, ' ')

class Game:
    def __init__(self):
        self.active = False
        self.surprise_box = None
        self.users_found = []
        self.users_not_found = []
        self.start_time = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(__("Команда /start для начала игры."))


async def start_game(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text(
            __("Эта игра может быть начата только в групповом чате.")
        )
        return

    game = context.chat_data.get("game", Game())

    if game.active:
        await update.message.reply_text("Игра уже идет!")
        return

    game.active = True
    game.surprise_box = random.randint(1, 9)
    game.users_found.clear()
    game.users_not_found.clear()
    game.start_time = time.time()
    context.chat_data["game"] = game  # Store the game in chat_data

    logger.info(__(f"Игра начата: писюн в коробке {game.surprise_box}"))

    await send_game_message(update, game)


async def send_game_message(update: Update, game: Game) -> None:
    keyboard = await create_keyboard()

    await update.message.reply_text(
        text=__("Нажмите на коробку, чтобы найти писюн!"), reply_markup=keyboard
    )


async def create_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for _ in range(1, 10):
        buttons.append([InlineKeyboardButton("📦", callback_data=str(_))])

    buttons.append(
        [
            InlineKeyboardButton(__("Закончить игру"), callback_data="end_game"),
        ],
    )
    return InlineKeyboardMarkup(buttons)


async def box_clicked(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    game = context.chat_data.get("game")

    if game is None or not game.active:
        await query.edit_message_text(text=__("Игра еще не началась!"))
        return

    box_number = int(query.data)

    user_name = query.from_user.first_name
    if user_name in game.users_found or user_name in game.users_not_found:
        await query.edit_message_text(text=__("Вы уже нажимали на коробку!"))
        return

    if box_number == game.surprise_box:
        game.users_found.append(user_name)
        result_message = f"{user_name} 🍌"
    else:
        game.users_not_found.append(user_name)
        result_message = f"{user_name} ❌"

    logger.info(result_message)

    await update_status(query.message, result_message, game)


async def update_status(message, result_message: str, game: Game) -> None:
    keyboard = await create_keyboard()

    status = __("Статус игры:\n")
    if game.users_found:
        status += "Нашли: " + ", ".join(game.users_found) + "\n"
    if game.users_not_found:
        status += "Не нашли: " + ", ".join(game.users_not_found) + "\n"

    if not game.users_found and not game.users_not_found:
        status += __("Никто ничего не нашел")
    await message.edit_text(
        text=f"{result_message}\n\n{status}", reply_markup=keyboard
    )


async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    game = context.chat_data.get("game")
    if game is None or not game.active:
        await query.edit_message_text(text=__("Игра еще не началась!"))
        return

    user_name = query.from_user.first_name

    if (
        user_name not in game.users_found
        and user_name not in game.users_not_found
    ):
        await query.edit_message_text(
            text=__("Вы ещё не нажали на коробку!")
        )
        await update_status(
            query.message,
            __("Вы ещё не нажали на коробку!"),
            game,
        )
        return
    else:
        game.active = False

        logger.info(
            f"Игра окончена: нашли - {game.users_found}, не  - {game.users_not_found}"
        )

        final_status = __("Игра окончена!\n")
        final_status += __("Нашли: " + ", ".join(game.users_found) + "\n")
        final_status += __("Не нашли: " + ", ".join(game.users_not_found) + "\n")

        await query.edit_message_text(
            text=final_status,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            __("еще одну игру"), callback_data="end_game1"
                        ),
                    ],
                ],
            ),
        )


application = (
    ApplicationBuilder()
    .token(settings.bot_token)
    .build()
)

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("start_game", start_game))
application.add_handler(CallbackQueryHandler(box_clicked, pattern="^[1-9]$"))
application.add_handler(CallbackQueryHandler(end_game, pattern="end_game"))

application.run_polling()
