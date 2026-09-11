"""Базовый DAG-основа хранилища DailyPay.

Каркас пайплайна: start → extract (S3/MinIO) → load → end.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

_SCRIPTS = Path("/opt/airflow/scripts")
if not _SCRIPTS.exists():
    _SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from extract_s3 import extract_from_s3  # noqa: E402


def extract(**context) -> dict:
    payload = extract_from_s3(logical_date=context["ds"])
    print(f"foundation extract: {payload}")
    return payload


def load(**context) -> str:
    # Заглушка загрузки. Следующий шаг: писать в Postgres finance_dwh.
    payload = context["ti"].xcom_pull(task_ids="extract")
    print(f"foundation load: {payload}")
    return "ok"


with DAG(
    dag_id="dailypay_foundation",
    description="Простой DAG-основа хранилища DailyPay с извлечением из S3",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args={
        "owner": "dailypay",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["dailypay", "foundation", "s3"],
) as dag:
    start = EmptyOperator(task_id="start")
    extract_task = PythonOperator(task_id="extract", python_callable=extract)
    load_task = PythonOperator(task_id="load", python_callable=load)
    end = EmptyOperator(task_id="end")

    start >> extract_task >> load_task >> end
