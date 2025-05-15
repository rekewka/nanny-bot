from dotenv import load_dotenv
import os 

load_dotenv()

TELEGRAM_TOKEN=os.getenv("TELEGRAM_TOKEN")
DB_URI=os.getenv("DB_URI")
