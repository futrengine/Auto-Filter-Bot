from pyrogram import Client, filters, types
from database import db
from config import Config
import math

# --- Helper: Convert Bytes to Readable Size ---
def get_size(size):
    if not size:
        return "0B"
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

# --- Auto Save New Files (Updated for Size) ---
@Client.on_message(filters.channel & (filters.document | filters.video | filters.audio))
async def auto_save_files(bot, message):
    channels_cursor = await db.get_db_channels()
    db_channels = [ch['chat_id'] async for ch in channels_cursor]
    
    if message.chat.id in db_channels:
        media = message.document or message.video or message.audio
        file_info = {
            "file_id": media.file_id,
            "file_unique_id": media.file_unique_id,
            "file_name": media.file_name or "Unknown",
            "file_size": media.file_size or 0, # Saving Size
            "caption": message.caption or media.file_name or "None",
            "file_type": media.mime_type
        }
        await db.save_file(file_info)
        print(f"Auto saved file from {message.chat.title}")

# --- User Search Logic (With Buttons) ---
@Client.on_message(filters.private & filters.text & ~filters.command(["start", "admin", "broadcast", "add_channel", "index"]))
async def search_handler(bot, message):
    user_id = message.from_user.id
    
    # 1. ADMIN BYPASS & SUBSCRIPTION CHECK
    if user_id != Config.ADMIN_ID:
        try:
            await bot.get_chat_member(Config.FORCE_SUB_CHANNEL, user_id)
        except:
            await message.reply_text(
                "**⚠️ You must join our update channel to use this bot!**",
                reply_markup=types.InlineKeyboardMarkup([
                    [types.InlineKeyboardButton("Join Channel", url=Config.FORCE_SUB_INVITE_LINK)],
                    [types.InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{bot.me.username}?start=start")]
                ])
            )
            return

    query = message.text
    msg = await message.reply_text("🔎 Searching files...")
    
    results = await db.search_files(query)
    
    if not results:
        return await msg.edit_text(f"❌ No files found for: **{query}**")

    # Send First Page (Page 0)
    await send_results(msg, results, 0, query)

# --- Pagination Function ---
async def send_results(message, results, page, query):
    RESULTS_PER_PAGE = 8
    total_results = len(results)
    total_pages = math.ceil(total_results / RESULTS_PER_PAGE)
    
    # Slice the results for current page
    start = page * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    current_page_results = results[start:end]
    
    buttons = []
    
    # File Buttons
    for file in current_page_results:
        size = get_size(file.get('file_size', 0))
        # Button: "Filename [100MB]" -> Callback: "send_OBJECTID"
        buttons.append([
            types.InlineKeyboardButton(
                f"{file['file_name']} [{size}]", 
                callback_data=f"send_{file['_id']}"
            )
        ])
    
    # Navigation Buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Back", callback_data=f"page_{page-1}_{query}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}_{query}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
        
    await message.edit_text(
        text=f"**Found {total_results} results for '{query}'**\nPage {page+1}/{total_pages}",
        reply_markup=types.InlineKeyboardMarkup(buttons)
    )