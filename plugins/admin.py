from pyrogram import Client, filters, types
from config import Config
from database import db
import asyncio

# --- Admin Panel UI ---
@Client.on_message(filters.command("admin"))
async def admin_panel(bot, message):
    # Security Check
    if message.from_user.id != Config.ADMIN_ID:
        # Optional: Print ID to console for debugging if needed
        # print(f"Unauthorized access attempt by: {message.from_user.id}") 
        return

    buttons = [
        [types.InlineKeyboardButton("Add DB Channel", callback_data="add_db_chan")],
        [types.InlineKeyboardButton("Broadcast", callback_data="broadcast_msg")]
    ]
    await message.reply_text("✅ Welcome to Admin Panel", reply_markup=types.InlineKeyboardMarkup(buttons))

# --- Add DB Channel Logic ---
@Client.on_callback_query(filters.regex("add_db_chan") & filters.user(Config.ADMIN_ID))
async def add_channel_ask(bot, callback):
    await callback.message.edit_text(
        "⚠️ **Interaction Error**\n\n"
        "I cannot read your replies directly yet.\n\n"
        "Please copy the Channel ID and use this command:\n"
        "`/add_channel -100xxxxxxx`"
    )

@Client.on_message(filters.command("add_channel") & filters.user(Config.ADMIN_ID))
async def add_channel_db(bot, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/add_channel -100xxxxxx`")
    
    try:
        chat_id = int(message.command[1])
        await db.add_channel(chat_id)
        await message.reply(f"✅ Channel {chat_id} added to Database.\nNow send `/index {chat_id}` to load existing files.")
    except ValueError:
        await message.reply("❌ Invalid ID format. Use numeric ID like -100123456789")

# --- Indexing Logic (The Fix for [400 BOT_METHOD_INVALID]) ---
@Client.on_message(filters.command("index") & filters.user(Config.ADMIN_ID))
async def index_channel(bot, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `/index -100xxxxxx`")
    
    chat_id = int(message.command[1])
    status_msg = await message.reply("🔄 Initializing Indexing...")
    
    try:
        # Step 1: Get the Last Message ID to know where to stop
        dummy = await bot.send_message(chat_id, "Indexing Check...")
        last_msg_id = dummy.id
        await dummy.delete()
    except Exception as e:
        return await status_msg.edit(f"❌ Error: Make sure I am Admin in {chat_id} with 'Post Messages' permission.\nError: {e}")

    total_files = 0
    await status_msg.edit(f"⏳ Indexing started from ID: {last_msg_id}...")

    # Step 2: Loop backwards from last message to 1
    # We fetch in batches of 200 (Telegram API limit for get_messages)
    for i in range(last_msg_id, 0, -200):
        try:
            # Create a list of IDs: [1000, 999, ... 801]
            ids = list(range(i, max(0, i - 200), -1))
            
            # Use get_messages (This works for bots!)
            messages = await bot.get_messages(chat_id, ids)
            
            for m in messages:
                # Skip empty or service messages
                if not m or m.empty:
                    continue
                
                media = m.document or m.video or m.audio
                if media:
                    file_info = {
                        "file_id": media.file_id,
                        "file_unique_id": media.file_unique_id,
                        "file_name": media.file_name or "Unknown",
                        "caption": m.caption or media.file_name or "None",
                        "file_type": media.mime_type
                    }
                    if await db.save_file(file_info):
                        total_files += 1
            
            # Update status every 1000 messages checked
            if i % 1000 == 0: 
                await status_msg.edit(f"📂 Indexed {total_files} files so far...\nCurrent ID: {i}")
                
        except Exception as e:
            print(f"Error in batch starting {i}: {e}")
            continue

    await status_msg.edit(f"✅ **Indexing Complete!**\n\nTotal Files Saved: {total_files}")

# --- Broadcast Logic ---
@Client.on_callback_query(filters.regex("broadcast_msg") & filters.user(Config.ADMIN_ID))
async def broadcast_trigger(bot, callback):
    await callback.message.edit_text("Reply to a message with `/broadcast` to send it to all users.")

@Client.on_message(filters.command("broadcast") & filters.reply & filters.user(Config.ADMIN_ID))
async def broadcast_handler(bot, message):
    users = await db.get_all_users()
    msg = await message.reply(" Broacasting...")
    done = 0
    failed = 0
    
    async for user in users:
        try:
            await message.reply_to_message.copy(chat_id=user['id'])
            done += 1
            await asyncio.sleep(0.1)
        except:
            failed += 1
            
    await msg.edit_text(f"Broadcast Complete.\nSuccess: {done}\nFailed: {failed}")