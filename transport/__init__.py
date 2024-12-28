import os
import toml
from dotenv import load_dotenv


BASE = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(dotenv_path=os.path.join(BASE, "extras", ".env"))


with open(os.path.join(BASE, "config.toml")) as f:
    CONFIG = toml.load(f)

assert 0 < CONFIG["transport"]["refresh_interval"] <= 60, "refresh interval must be between 0 and 60"
