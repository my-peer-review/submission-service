import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env: str = "development"
    jwt_algorithm: str
    jwt_public_key_path: str
    jwt_private_key_path: str
    mongo_uri: str
    mongo_db_name: str

    class Config:
        env_file = ".env"

# Override dinamico dell'env_file
env = os.getenv("ENV", "development")
env_file = f".env.{env}" if env != "development" else ".env.test"

settings = Settings(_env_file=env_file)