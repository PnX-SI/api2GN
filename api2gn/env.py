from pathlib import Path
from types import SimpleNamespace
from dotenv import dotenv_values


MODULE_DIR = Path(__file__).absolute().parent
ENV = SimpleNamespace(**dotenv_values(str(MODULE_DIR / "var/config/.env")))
