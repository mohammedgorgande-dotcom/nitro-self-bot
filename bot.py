# ==========================================================
# نیترو سلف - مرحله ۳ (مرحله نهایی: ظاهر دقیقاً طبق تصویر)
# ==========================================================
import sqlite3
import logging
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

TOKEN = "8475834635:AAG8KZS3P_8R9heBcJGddcEmtmbmnZbw0OE"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

INITIAL_DIAMONDS = 100

# ----------------- بخش ۱: دیتابیس -----------------
def init_db():
    conn = sqlite3.connect("gemino.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            diamonds INTEGER DEFAULT 100
        )
    """)
    conn.commit()
    conn.close()

def get_diamonds(user_id: int) -> int:
    conn = sqlite3.connect("gemino.db")
    cursor = conn.cursor()
    cursor.execute("SELECT diamonds FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO users (user_id, diamonds) VALUES (?, ?)", (user_id, INITIAL_DIAMONDS))
        conn.commit()
        conn.close()
        return INITIAL_DIAMONDS
    conn.close()
    return res[0]

def update_diamonds(user_id: int, amount: int):
    conn = sqlite3.connect("gemino.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET diamonds = diamonds + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# ----------------- بخش ۲: دستورات اولیه -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    diamonds = get_diamonds(user.id)
    
    welcome_text = (
        f"سلام {user.first_name} عزیز! 💎\n"
        f"به ربات شرط‌بندی نیترو سلف خوش آمدید.\n\n"
        f"💰 موجودی فعلی شما: **{diamonds:,} الماس**"
    )
    
    keyboard = [
        [InlineKeyboardButton("💎 استعلام موجودی", callback_data="check_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

# ----------------- بخش ۳: پردازش پیام‌های گروه -----------------
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user = update.effective_user

    # استعلام موجودی سریع با ریپلای
    if text == "موجودی" or text == "/balance":
        diamonds = get_diamonds(user.id)
        reply_text = f"👤 {user.first_name}\n💎 موجودی شما: **{diamonds:,} الماس**"
        await update.message.reply_text(
            reply_text,
            reply_to_message_id=update.message.message_id,
            parse_mode="Markdown"
        )
        return

    # ساخت بازی جدید (مثال: بازی 197)
    if text.startswith("بازی "):
        parts = text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return

        bet_amount = int(parts[1])
        if bet_amount <= 0:
            return

        p1_diamonds = get_diamonds(user.id)
        if p1_diamonds < bet_amount:
            await update.message.reply_text(f"❌ موجودی کافی نیست. (موجودی: {p1_diamonds:,} الماس)")
            return

        context.chat_data['active_game'] = {
            'p1_id': user.id,
            'p1_name': user.username if user.username else user.first_name,
            'amount': bet_amount
        }

        # کارت بازی تمیز طبق نمونه تصویر
        caption_text = (
            f"◈ ━━━ nitro self ━━━ ◈\n"
            f"👤 سازنده: {user.first_name}\n"
            f"💎 مقدار: {bet_amount:,} الماس\n"
            f"◈ ━━━ nitro self ━━━ ◈"
        )

        keyboard = [
            [
                InlineKeyboardButton("🟩 پیوستن", callback_data="join_game"),
                InlineKeyboardButton("❌ لغو شرط", callback_data="cancel_game")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(caption_text, reply_markup=reply_markup, parse_mode="Markdown")

# ----------------- بخش ۴: پردازش دکمه‌ها و نتیجه بازی -----------------
async def callback_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if query.data == "check_balance":
        await query.answer()
        diamonds = get_diamonds(user.id)
        await query.message.edit_text(f"💎 موجودی فعلی شما: **{diamonds:,} الماس**", parse_mode="Markdown")
        return

    game = context.chat_data.get('active_game')

    # کلیک روی پیوستن
    if query.data == "join_game":
        if not game:
            await query.answer("این بازی منقضی شده است.", show_alert=True)
            return

        if user.id == game['p1_id']:
            await query.answer("شما سازنده این چالش هستید!", show_alert=True)
            return

        p2_diamonds = get_diamonds(user.id)
        bet_amount = game['amount']

        if p2_diamonds < bet_amount:
            await query.answer(f"موجودی کافی نیست! ({bet_amount:,} الماس نیاز است)", show_alert=True)
            return

        p1_id = game['p1_id']
        p1_name = game['p1_name']
        p2_id = user.id
        p2_name = user.username if user.username else user.first_name

        context.chat_data['active_game'] = None
        await query.answer()

        # انتخاب تصادفی برنده و بازنده
        if random.choice([True, False]):
            winner_id, winner_name = p1_id, p1_name
            loser_id, loser_name = p2_id, p2_name
        else:
            winner_id, winner_name = p2_id, p2_name
            loser_id, loser_name = p1_id, p1_name

        # محاسبات مالیکارمزد (۲ به ازای هر ۲۰ شرط)
        fee_per_20 = 2
        total_fee = max(1, int((bet_amount / 20) * fee_per_20))
        net_win = bet_amount - total_fee

        update_diamonds(loser_id, -bet_amount)
        update_diamonds(winner_id, net_win)

        # فرمت کارت نتیجه دقیقاً طبق تصویر نمونه
        result_text = (
            f"◈ ━━━ nitro self ━━━ ◈\n"
            f"🏆 برنده: {winner_name}\n"
            f"💔 بازنده: {loser_name}\n"
            f"🎁 جایزه: {bet_amount + net_win:,} الماس\n"
            f"💵 کارمزد: {total_fee:,} الماس\n"
            f"◈ ━━━ nitro self ━━━ ◈"
        )

        await query.message.edit_text(result_text, parse_mode="Markdown")

    # کلیک روی لغو شرط
    elif query.data == "cancel_game":
        if not game:
            await query.answer("بازی فعالی یافت نشد.", show_alert=True)
            return

        if user.id != game['p1_id']:
            await query.answer("فقط سازنده بازی می‌تواند آن را لغو کند!", show_alert=True)
            return

        context.chat_data['active_game'] = None
        await query.answer()
        # پیام لغو بازی طبق نمونه تصویر
        await query.message.edit_text("⌛ بازی لغو شد — کسی نپیوست.")

# ----------------- بخش ۵: اجرا -----------------
def main():
    init_db()

    app = (
        Application.builder()
        .token(TOKEN)
        .read_timeout(30)
        .connect_timeout(30)
        .write_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(callback_dispatcher))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))

    print("🚀 پروژه ساخت ربات نیترو سلف به طور کامل به پایان رسید!")

    while True:
        try:
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    main()
  
