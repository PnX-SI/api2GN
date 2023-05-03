from pathlib import Path
from toml import load
from api2gn.schema import SyntheseSchema, ImportSchema

config = load(Path("config.toml"))
