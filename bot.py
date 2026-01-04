from pyrogram import Client, idle
from config import Config
from aiohttp import web
import asyncio

# --- Web Server Code ---
routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running", "message": "Bot is active!"})

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app

# --- Bot Code ---
class Bot(Client):
    def __init__(self):
        super().__init__(
            "AutoFilterBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            plugins=dict(root="plugins")
        )

    async def start(self):
        await super().start()
        print("Bot Started Successfully!")

    async def stop(self, *args):
        await super().stop()
        print("Bot Stopped.")

# --- Main Execution ---
if __name__ == "__main__":
    app = Bot()
    
    loop = asyncio.get_event_loop()
    
    # 1. Start the Web Server (Port 8080 or Render's PORT env)
    import os
    PORT = int(os.environ.get("PORT", 8080))
    app_runner = web.AppRunner(loop.run_until_complete(web_server()))
    loop.run_until_complete(app_runner.setup())
    site = web.TCPSite(app_runner, "0.0.0.0", PORT)
    loop.run_until_complete(site.start())
    
    # 2. Start the Bot
    loop.run_until_complete(app.start())
    
    # 3. Keep running
    print(f"Web Server running on Port {PORT}")
    idle()