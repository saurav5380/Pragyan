import os
from pydantic import BaseModel

class Settings(BaseModel):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgresql:root@127.0.0.1:5433/pragyan"
    )

settings = Settings()
