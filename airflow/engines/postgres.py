import os

from sqlalchemy import create_engine


def postgres_url() -> str:
    """Собирает URL хранилища finance_dwh внутри Docker-сети."""
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ.get("POSTGRES_HOST", "postgres")
    database = os.environ["POSTGRES_DB"]
    return f"postgresql+psycopg2://{user}:{password}@{host}/{database}"


postgres_engine = create_engine(postgres_url())
