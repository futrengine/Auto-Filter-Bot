from pyrogram import Client, filters, types
from pyrogram.errors import UserNotParticipant
from config import Config
from database import db
from plugins.filters import send_results # Import the pagination function

# Check Subscription Logic
async def is_subscribed(bot, user_id):
    try:
        await bot.get_chat_member(Config.FORCE_SUB_CHANNEL, user_id)
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True 

@Client.on_message(filters.command("start") & filters.private)
async def start_handler(bot, message):
    user_id = message.from_user.id
    await db.add_user(user_id)
    
    if user_id != Config.ADMIN_ID:
        subscribed = await is_subscribed(bot, user_id)
        if not subscribed:
            await message.reply_text(
                text="**⚠️ You must join our update channel to use this bot!**",
                reply_markup=types.InlineKeyboardMarkup([
                    [types.InlineKeyboardButton("Join Channel", url=Config.FORCE_SUB_INVITE_LINK)],
                    [types.InlineKeyboardButton("🔄 Try Again", callback_data="check_sub")]
                ])
            )
            return

    await message.reply_photo(
        photo=Config.START_PIC,
        caption=f"Hi {message.from_user.mention}, I am an Auto Filter Bot! Send me any movie name.",
        reply_markup=types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("Help", callback_data="help_msg")]
        ])
    )

@Client.on_callback_query(filters.regex("check_sub"))
async def refresh_sub(bot, callback):
    if callback.from_user.id == Config.ADMIN_ID:
        await callback.message.delete()
        await callback.message.reply_text("You are Admin. Welcome.")
        return

    subscribed = await is_subscribed(bot, callback.from_user.id)
    if subscribed:
        await callback.message.delete()
        await callback.message.reply_photo(
            photo=Config.START_PIC,
            caption="**Welcome Back! You can now use the bot.**",
        )
    else:
        await callback.answer("You have not joined yet!", show_alert=True)

@Client.on_callback_query(filters.regex("help_msg"))
async def help_handler(bot, callback):
    await callback.edit_message_caption(
        caption="**Help Module**\n\nJust send me the name of the file/movie you want.\n\n**Admin Commands:**\n/admin - Open Admin Panel",
        reply_markup=types.InlineKeyboardMarkup([[types.InlineKeyboardButton("Back", callback_data="check_sub")]])
    )

# --- CALLBACKS FOR FILES & PAGINATION ---

# 1. Handle Pagination (Next/Back)
@Client.on_callback_query(filters.regex(r"page_"))
async def page_callback(bot, callback):
    # Data format: "page_{page_number}_{query}"
    data = callback.data.split("_", 2)
    page = int(data[1])
    query = data[2]
    
    results = await db.search_files(query)
    await send_results(callback.message, results, page, query)

# 2. Handle File Sending
@Client.on_callback_query(filters.regex(r"send_"))
async def send_file_callback(bot, callback):
    # Data format: "send_{object_id}"
    file_oid = callback.data.split("_")[1]
    
    file_info = await db.get_file(file_oid)
    if not file_info:
        await callback.answer("File not found in DB!", show_alert=True)
        return
        
    try:
        await callback.message.reply_cached_media(
            file_info['file_id'],
            caption=f"📂 **{file_info['file_name']}**\n\n🤖 via @{bot.me.username}"
        )
        await callback.answer() # Close the loading circle
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)