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

header_length = 30


def __(text: str) -> str:
    return (
        text[: header_length - 3] + "..."
        if len(text) > header_length
        else text
    )


class Game:
    def __init__(self):
        self.active = False
        self.surprise_boxes = set()
        self.users_found = []
        self.users_not_found = []
        self.start_time = None
        self.results = []
        self.stupid_counter = 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(__("Команда /start для начала игры."))


async def start_game(
    update: Update, context: ContextTypes.DEFAULT_TYPE, new_message=True
) -> None:
    if update.message:
        chat_type = update.message.chat.type
    else:
        chat_type = update.callback_query.message.chat.type

    if chat_type not in ["group", "supergroup"]:
        await update.effective_message.reply_text(
            __("Эта игра может быть начата только в групповом чате.")
        )
        return

    game = context.chat_data.get("game", Game())

    if game.active:
        await update.effective_message.reply_text("Игра уже идет!")
        return

    game.active = True
    game.surprise_boxes = set(
        random.sample(range(1, 10), random.randint(1, 4))
    )
    game.users_found.clear()
    game.users_not_found.clear()
    game.results.clear()
    game.start_time = time.time()
    context.chat_data["game"] = game

    logger.info(f"Игра начата: писюны в коробках {game.surprise_boxes}")

    if new_message:
        await send_game_message(update, game)
    else:
        await update_status(update.callback_query.message, "", game)


async def send_game_message(update: Update, game: Game) -> None:
    keyboard = await create_keyboard()
    await update.message.reply_text(
        text=__("Нажмите на коробку, чтобы найти писюн!"),
        reply_markup=keyboard,
    )


async def create_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("📦", callback_data="1"),
            InlineKeyboardButton("📦", callback_data="2"),
            InlineKeyboardButton("📦", callback_data="3"),
        ],
        [
            InlineKeyboardButton("📦", callback_data="4"),
            InlineKeyboardButton("📦", callback_data="5"),
            InlineKeyboardButton("📦", callback_data="6"),
        ],
        [
            InlineKeyboardButton("📦", callback_data="7"),
            InlineKeyboardButton("📦", callback_data="8"),
            InlineKeyboardButton("📦", callback_data="9"),
        ],
        [InlineKeyboardButton("Закончить игру", callback_data="end_game")],
    ]
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

    try:
        box_number = int(query.data)
    except ValueError:
        await query.edit_message_text(text=__("Неверный выбор!"))
        return

    user_name = query.from_user.first_name
    if user_name in game.users_found or user_name in game.users_not_found:
        await update_status(
            query.message, __(f"{user_name} хочет еще член!"), game
        )
        return

    if box_number in game.surprise_boxes:
        game.users_found.append(user_name)
        result_message = f"{user_name}: 🍆 нашёл(ла) член"
    else:
        game.users_not_found.append(user_name)
        result_message = f"{user_name}: 💨 открыл(а) пустую коробку"

    game.results.append(result_message)
    logger.info(result_message)

    await update_status(query.message, result_message, game)


async def update_status(message, result_message: str, game: Game) -> None:
    keyboard = await create_keyboard()
    status = __("Статус игры:\n")
    status += "\n".join(game.results)

    if result_message:
        status = "\n".join(
            (result_message, "\n", status, "\n"),
        )

    await message.edit_text(text=f"{status}", reply_markup=keyboard)


async def counter(message, game: Game) -> None:
    if game is None:
        await query.edit_message_text(text=__("Игра еще не началась!"))
        return
    game.counter += 1
    await message.update_text(
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        __(f"Кнопка для нетерпеливых: {game.counter}"),
                        callback_data="counter",
                    )
                ]
            ]
        ),
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
        await update_status(
            query.message,
            __(f"{user_name} хочет всех обломать"),
            game,
        )
        return

    game.active = False
    logger.info(
        f"Игра окончена: нашли - {game.users_found}, не - {game.users_not_found}"
    )

    final_status = __("Игра окончена!\n")
    final_status += "\n".join(game.results)

    await query.edit_message_text(
        text=final_status,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        __("Кнопка для нетерпеливых "), callback_data="counter"
                    )
                ]
            ]
        ),
    )


application = ApplicationBuilder().token(settings.bot_token).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("start_game", start_game))
application.add_handler(CallbackQueryHandler(box_clicked, pattern="^[1-9]$"))
application.add_handler(CallbackQueryHandler(end_game, pattern="end_game"))
application.add_handler(
    CallbackQueryHandler(
        lambda update, context: start_game(update, context),
        pattern="start_game",
    )
)
application.add_handler(
    CallbackQueryHandler(
        lambda update, context: counter(update, context), pattern="start_game"
    )
)

application.run_polling()
