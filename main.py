import logging
import random
import time
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Game:
    def __init__(self):
        self.active = False
        self.surprise_box = None
        self.users_found = []
        self.users_not_found = []
        self.start_time = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Команда /start для начала игры.")

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if the command is used in a group chat
    if update.message.chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Эта игра может быть начата только в групповом чате.")
        return

    game = context.chat_data.get('game', Game())

    if game.active:
        await update.message.reply_text("Игра уже идет!")
        return

    game.active = True
    game.surprise_box = random.randint(1, 9)
    game.users_found.clear()
    game.users_not_found.clear()
    game.start_time = time.time()
    context.chat_data['game'] = game  # Store the game in chat_data

    logger.info(f"Игра начата: писюн в коробке {game.surprise_box}")

    await send_game_message(update, game)

async def send_game_message(update: Update, game: Game) -> None:
    keyboard = await create_keyboard()

    # Send the initial game message
    await update.message.reply_text(
        text="Нажмите на коробку, чтобы найти писюн!",
        reply_markup=keyboard
    )

async def create_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📦", callback_data='1'), InlineKeyboardButton("📦", callback_data='2'), InlineKeyboardButton("📦", callback_data='3')],
        [InlineKeyboardButton("📦", callback_data='4'), InlineKeyboardButton("📦", callback_data='5'), InlineKeyboardButton("📦", callback_data='6')],
        [InlineKeyboardButton("📦", callback_data='7'), InlineKeyboardButton("📦", callback_data='8'), InlineKeyboardButton("📦", callback_data='9')],
        [InlineKeyboardButton("Закончить игру", callback_data='end_game')]  # Add End Game button here
    ]
    return InlineKeyboardMarkup(buttons)

async def box_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    game = context.chat_data.get('game')

    if game is None or not game.active:
        await query.edit_message_text(text="Игра еще не началась!")
        return

    box_number = int(query.data)

    # Check if the user has already clicked
    user_name = query.from_user.first_name
    if user_name in game.users_found or user_name in game.users_not_found:
        await query.edit_message_text(text="Вы уже нажимали на коробку!")
        return

    # Determine if the user found the surprise
    if box_number == game.surprise_box:
        game.users_found.append(user_name)
        result_message = f"{user_name} нашел писюн!"
    else:
        game.users_not_found.append(user_name)
        result_message = f"{user_name} не нашел писюн."

    logger.info(result_message)

    await update_status(query.message, result_message, game)

async def update_status(message, result_message: str, game: Game) -> None:
    # Create keyboard for ending the game
    keyboard = await create_keyboard()  # Include the End Game button

    # Create game status
    status = "Статус игры:\n"
    status += "Нашли: " + ", ".join(game.users_found) + "\n"
    status += "Не нашли: " + ", ".join(game.users_not_found) + "\n"
    
    # Update the message
    await message.edit_text(text=f"{result_message}\n\n{status}", reply_markup=keyboard)

async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    game = context.chat_data.get('game')
    if game is None or not game.active:
        await query.edit_message_text(text="Игра еще не началась!")
        return

    user_name = query.from_user.first_name

    # Allow any user who has participated to end the game
    if user_name not in game.users_found and user_name not in game.users_not_found:
        await query.edit_message_text(text="Вы не можете закончить игру, если не нажимали на коробки.")
        await update_status(query.message, "Вы не можете закончить игру, если не нажимали на коробки.", game)
        return
    else:
        game.active = False

        logger.info(f"Игра окончена: нашедшие - {game.users_found}, не нашедшие - {game.users_not_found}")

        # Create final summary message
        final_status = "Игра окончена!\n"
        final_status += "Нашли: " + ", ".join(game.users_found) + "\n"
        final_status += "Не нашли: " + ", ".join(game.users_not_found) + "\n"
        
        # Remove the buttons and update the message
        await query.edit_message_text(
            text=final_status,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("а все уже", callback_data='end_game1'), ],
            ],
            )
        )

application = ApplicationBuilder().token("433981632:AAGmOpyrz0y51Lmxozwm3tWqxsUQ6UhJcYg").build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("start_game", start_game))
application.add_handler(CallbackQueryHandler(box_clicked, pattern='^[1-9]$'))
application.add_handler(CallbackQueryHandler(end_game, pattern='end_game'))

# Remove timeout job
logger.info("Timeout job has been disabled.")

application.run_polling()

