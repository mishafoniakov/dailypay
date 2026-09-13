from sqlalchemy import text
from pangres import upsert

from engines.postgres import postgres_engine

SCHEMA = "raw"
KIND_TABLE = {
    "расход": "expense",
    "доход": "income",
}
COLUMNS = ["txn_date", "payee", "category", "description", "envelope", "amount"]
PK = ["txn_date", "category", "envelope", "amount"]


class PostgresLoader:
    """Пишет расход и доход в схему raw."""

    def __init__(self, engine=postgres_engine):
        """Подключает загрузчик к движку Postgres."""
        self.engine = engine

    def load(self, df, kind: str, source_file: str) -> dict[str, int]:
        """Заменяет строки этого PDF и вставляет расход и доход."""
        name = KIND_TABLE[kind]
        with self.engine.begin() as conn:
            return {name: self._replace(conn, df, kind, name, source_file)}

    def _replace(self, conn, df, kind: str, name: str, source_file: str) -> int:
        """Обновляет одну таблицу строками выбранного типа из DataFrame."""
        conn.execute(
            text(f"DELETE FROM {SCHEMA}.{name} WHERE source_file = :source_file"),  # SQL: удалить старые строки этого PDF в raw
            {"source_file": source_file},  # подставить имя файла в :source_file
        )
        part = df[df["kind"] == kind] if "kind" in df.columns else df.iloc[0:0]  # взять расход или доход; без kind — пустой срез
        rows = part.rename(columns={"date": "txn_date"})[COLUMNS].assign(source_file=source_file)  # date→txn_date, нужные колонки, пометить файл
        rows[["category", "envelope"]] = rows[["category", "envelope"]].fillna("")  # NULL в PK-полях заменить на пустую строку
        rows = rows.drop_duplicates(subset=PK, keep="last")  # индекс pangres должен быть уникальным
        if not rows.empty:  # не вызывать upsert, если после фильтра ничего нет
            upsert(
                con=conn,  # та же транзакция, что и DELETE
                df=rows.set_index(PK),  # индекс = PRIMARY KEY таблицы
                table_name=name,  # expense или income
                schema=SCHEMA,  # писать в raw, не в public
                if_row_exists="update",  # ON CONFLICT DO UPDATE (не if_exists)
                create_table=False,  # таблицу уже создаёт SQL-файл
            )
        return len(rows)  # сколько строк ушло в эту таблицу
