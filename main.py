import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from fpdf import FPDF

# --- CONFIG ---
BOT_TOKEN = "7693918135:AAGO-4A2lCRMaDnpmItkOY94w1f16_D0iSw"  # Replace with your actual bot token
UPI_ID = "work.piyush006@fam"
QR_IMAGE_PATH = "Qr.png"
PREMIUM_FILE = "user_premium.txt"
USER_SEEN_FILE = "user.txt"
IMAGE_LIMIT = 7
PDF_LIMIT = 7
ADMIN_USERNAME = "Image2pdfadmin"

# --- Runtime Data ---
PREMIUM_USERS = set()
USER_IMAGES = {}
USER_USAGE = {}
LAST_REQUEST_TIME = {}

# --- Load Premium Users ---
if os.path.exists(PREMIUM_FILE):
    with open(PREMIUM_FILE, 'r') as f:
        for line in f:
            try:
                PREMIUM_USERS.add(int(line.strip()))
            except:
                continue

# --- PDF Generator ---
def create_pdf(images, filename):
    pdf = FPDF()
    for img in images:
        pdf.add_page()
        pdf.image(img, x=10, y=10, w=190)
    pdf.output(filename)

# --- Helper ---
def is_premium(user_id):
    return user_id in PREMIUM_USERS

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USER_USAGE.setdefault(user_id, {'images_used': 0, 'pdfs_generated': 0})
    USER_IMAGES.setdefault(user_id, [])

    keyboard = [
        [InlineKeyboardButton("🖼️ Send Images", callback_data='send')],
        [InlineKeyboardButton("📄 Create PDF", callback_data='convert')],
        [InlineKeyboardButton("🗑️ Clear All", callback_data='clear')],
        [InlineKeyboardButton("💳 Get Premium", callback_data='get_premium')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_premium(user_id):
        await update.message.reply_text(
            "🎉 You're a *PREMIUM* user!\n\n👇 Choose an option:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        now = time.time()
        last = LAST_REQUEST_TIME.get(user_id, 0)
        if now - last > 43200:
            LAST_REQUEST_TIME[user_id] = now
            await update.message.reply_text(
                f"⏰ *Reminder*: Pay ₹29 to `{UPI_ID}` and send screenshot with your ID: `{user_id}` to admin.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📤 Send to Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
                ])
            )

        await update.message.reply_text(
            "👋 Welcome to Image2PDF Bot!\n\n"
            "📷 Free users: *7 images* & *7 PDFs* limit.\n"
            "✨ Premium: Unlimited access.\n\n"
            f"🆔 Your ID: `{user_id}`",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

# --- BUTTONS ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    USER_USAGE.setdefault(user_id, {'images_used': 0, 'pdfs_generated': 0})
    USER_IMAGES.setdefault(user_id, [])

    if query.data == 'send':
        await query.edit_message_text("📤 Send your images now.")

    elif query.data == 'convert':
        await convert_from_button(query, context)

    elif query.data == 'clear':
        for img in USER_IMAGES[user_id]:
            if os.path.exists(img):
                os.remove(img)
        USER_IMAGES[user_id] = []
        await query.edit_message_text("🗑️ All images cleared.")

    elif query.data == 'get_premium':
        if not os.path.exists(USER_SEEN_FILE):
            open(USER_SEEN_FILE, "w").close()

        with open(USER_SEEN_FILE, "r") as f:
            seen_ids = [line.strip() for line in f]

        if str(user_id) not in seen_ids:
            with open(USER_SEEN_FILE, "a") as f:
                f.write(str(user_id) + "\n")

        if is_premium(user_id):
            await query.edit_message_text(
                "🌟 You're already a *Premium* member!\nEnjoy unlimited features!",
                parse_mode='Markdown'
            )
            return

        if os.path.exists(QR_IMAGE_PATH):
            with open(QR_IMAGE_PATH, 'rb') as qr:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=qr,
                    caption=(
                        "💳 *Upgrade to Premium (₹29)*\n\n"
                        f"Pay to UPI: `{UPI_ID}`\n"
                        f"🆔 Your ID: `{user_id}`\n"
                        "📩 After payment, send screenshot to admin."
                    ),
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Send to Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
                    ])
                )
        else:
            await query.edit_message_text(
                f"💳 *Pay ₹29 to unlock Premium*\n\nUPI: `{UPI_ID}`\n🆔 Your ID: `{user_id}`",
                parse_mode='Markdown'
            )

# --- CONVERT TO PDF ---
async def convert_from_button(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(update_or_query, Update):
        user_id = update_or_query.message.from_user.id
        reply = update_or_query.message.reply_text
    else:
        user_id = update_or_query.from_user.id
        reply = update_or_query.edit_message_text

    images = USER_IMAGES.get(user_id, [])
    if not images:
        await reply("❗ No images found.")
        return

    if not is_premium(user_id) and USER_USAGE[user_id]['pdfs_generated'] >= PDF_LIMIT:
        await reply("🚫 Free PDF limit reached. Upgrade to Premium.")
        return

    filename = f"{user_id}_output.pdf"
    create_pdf(images, filename)

    with open(filename, 'rb') as f:
        await context.bot.send_document(chat_id=user_id, document=f, filename="Image2PDFMaster.pdf")

    for img in images:
        os.remove(img)
    os.remove(filename)
    USER_IMAGES[user_id] = []

    if not is_premium(user_id):
        USER_USAGE[user_id]['pdfs_generated'] += 1

    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ PDF created!\nUsed: {USER_USAGE[user_id]['pdfs_generated']} of {PDF_LIMIT}."
    )

# --- IMAGE HANDLER ---
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    USER_IMAGES.setdefault(user_id, [])
    USER_USAGE.setdefault(user_id, {'images_used': 0, 'pdfs_generated': 0})

    if not is_premium(user_id) and USER_USAGE[user_id]['images_used'] >= IMAGE_LIMIT:
        await update.message.reply_text("🚫 Image limit reached.")
        return

    file = await update.message.photo[-1].get_file()
    img_path = f"{user_id}_{len(USER_IMAGES[user_id])}.jpg"
    await file.download_to_drive(img_path)
    USER_IMAGES[user_id].append(img_path)

    if not is_premium(user_id):
        USER_USAGE[user_id]['images_used'] += 1

    await update.message.reply_text("🖼 Image saved!")

# --- ERROR HANDLER ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"⚠️ Error: {context.error}")

# --- MAIN ---
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.add_error_handler(error_handler)

    print("🤖 Bot is running...")
    app.run_polling()