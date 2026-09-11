"""Базовый DAG-основа хранилища DailyPay.

Каркас пайплайна: start → extract → load → end.
Дальше в эти шаги можно подставлять MinIO, Postgres и реальные источники.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator


def extract(**context) -> dict:
    # Заглушка извлечения. Следующий шаг: читать сырьё из MinIO / источника.
    payload = {"source": "stub", "rows": 0, "ds": context["ds"]}
    print(f"foundation extract: {payload}")
    return payload


def load(**context) -> str:
    # Заглушка загрузки. Следующий шаг: писать в Postgres finance_dwh.
    payload = context["ti"].xcom_pull(task_ids="extract")
    print(f"foundation load: {payload}")
    return "ok"


with DAG(
    dag_id="dailypay_foundation",
    description="Простой DAG-основа хранилища DailyPay",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args={
        "owner": "dailypay",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["dailypay", "foundation"],
) as dag:
    start = EmptyOperator(task_id="start")
    extract_task = PythonOperator(task_id="extract", python_callable=extract)
    load_task = PythonOperator(task_id="load", python_callable=load)
    end = EmptyOperator(task_id="end")

    start >> extract_task >> load_task >> end
