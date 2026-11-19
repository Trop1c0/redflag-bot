import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# ID канала/группы, куда падают заявки (например -1001234567890). Бот должен быть там админом.
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
# ID админов через запятую. Если пусто — кнопки могут жать админы канала.
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
TEAM_NAME = os.getenv("TEAM_NAME", "REDFLAG")
DB_PATH = os.getenv("DB_PATH", "bot.db")

if not BOT_TOKEN or not CHANNEL_ID:
    raise SystemExit("Заполни BOT_TOKEN и CHANNEL_ID в файле .env")
