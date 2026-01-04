import motor.motor_asyncio
from bson.objectid import ObjectId
from config import Config

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.files = self.db.files
        self.channels = self.db.channels

    # --- User Management ---
    async def add_user(self, id):
        user = await self.col.find_one({'id': int(id)})
        if not user:
            await self.col.insert_one({'id': int(id)})

    async def get_all_users(self):
        return self.col.find({})

    # --- File Management ---
    async def save_file(self, file_info):
        is_exist = await self.files.find_one({'file_unique_id': file_info['file_unique_id']})
        if not is_exist:
            await self.files.insert_one(file_info)
            return True
        return False

    async def search_files(self, query):
        # Return all matching files as a list
        cursor = self.files.find({"file_name": {"$regex": query, "$options": "i"}})
        return await cursor.to_list(length=None)

    async def get_file(self, _id):
        # Fetch a single file by its MongoDB Object ID
        try:
            return await self.files.find_one({"_id": ObjectId(_id)})
        except:
            return None

    # --- Channel Management ---
    async def add_channel(self, chat_id):
        channel = await self.channels.find_one({'chat_id': chat_id})
        if not channel:
            await self.channels.insert_one({'chat_id': chat_id})
            return True
        return False

    async def get_db_channels(self):
        return self.channels.find({})

db = Database(Config.MONGO_DB_URI, "AutoFilterBot")