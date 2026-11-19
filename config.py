import os
import sys

from dotenv import load_dotenv

# Файл настроек: python bot.py .env.bot2  (по умолчанию .env)
ENV_FILE = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ENV_FILE", ".env")
if not os.path.isfile(ENV_FILE):
    raise SystemExit(f"Файл настроек {ENV_FILE} не найден")
load_dotenv(ENV_FILE)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
# ID канала/группы, куда падают заявки (например -1001234567890). Бот должен быть там админом.
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
# ID админов через запятую. Если пусто — кнопки могут жать админы канала.
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
# 1 — управлять заявками могут все участники группы/канала заявок, 0 — только админы
ALLOW_ALL_MEMBERS = os.getenv("ALLOW_ALL_MEMBERS", "1") == "1"
TEAM_NAME =os.getenv("TEAM_NAME", "REDFLAG")
DB_PATH = os.getenv("DB_PATH", "bot.db")

if not BOT_TOKEN or not CHANNEL_ID:
    raise SystemExit("Заполни BOT_TOKEN и CHANNEL_ID в файле .env")
