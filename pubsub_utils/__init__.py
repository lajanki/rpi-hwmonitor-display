import os
from dotenv import load_dotenv


BASE = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(dotenv_path=os.path.join(BASE, ".env"))

PROJECT_ID = os.environ["PROJECT_ID"]
SUBSCRIPTION_ID = os.environ["SUBSCRIPTION_ID"]
TOPIC_ID = os.environ["TOPIC_ID"]
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "5"))