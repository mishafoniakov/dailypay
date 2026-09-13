import os

from airflow import DAG
from airflow.exceptions import AirflowFailException
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

from engines.minio import minio_client
from scripts.pdfextract import PDFExtractor
from scripts.postgresextract import PostgresLoader

def extract_all(**context) -> dict:
    """Списывает список объектов из бакета MinIO и кладёт его в XCom."""

    ti = context['ti']
    bucket = os.environ['MINIO_BUCKET']
    files = [
        {
            'key': obj.object_name,
            'size': obj.size,
            'last_modified': obj.last_modified.isoformat()
        }
        for obj in minio_client.list_objects(bucket, recursive=True)
    ]
    ti.xcom_push(key='bucket_files', value=files)
    ti.xcom_push(key='bucket_name', value=bucket)

    return {'bucket': bucket, 'count': len(files)}

def extract_one(**context) -> dict:
    """Выбирает самый свежий файл из списка extract_all и кладёт его в XCom."""

    ti = context["ti"]
    files = ti.xcom_pull(task_ids="extract_all", key='bucket_files') or []
    bucket = ti.xcom_pull(task_ids="extract_all", key='bucket_name')

    if not files:
        raise AirflowFailException(
            f"В бакете {bucket!r} нет объектов — extract_one не из чего выбирать"
        )

    sorted_files = sorted(files, key=lambda x: x['last_modified'], reverse=True)
    file = sorted_files[0]

    ti.xcom_push(key='bucket_file', value=file)
    ti.xcom_push(key='bucket_name', value=bucket)

    return {'bucket': bucket, 'file': file}

def load(kind, **context) -> dict:
    """Скачивает PDF из MinIO, разбирает расход и доход и пишет их в Postgres."""

    ti = context["ti"]
    bucket = ti.xcom_pull(task_ids="extract_one", key="bucket_name")
    file = ti.xcom_pull(task_ids="extract_one", key="bucket_file")

    response = minio_client.get_object(bucket, file["key"])
    try:
        pdf_bytes = response.read()
    finally:
        response.close()
        response.release_conn()

    df = PDFExtractor(pdf_bytes)()
    rows = PostgresLoader().load(df, kind, source_file=file["key"])
    return {"source_file": file["key"], "rows": rows}

with DAG(
    dag_id="etl",
    schedule=None,
    template_searchpath=["/data"],
) as dag:

    extract_all_task = PythonOperator(
        task_id="extract_all", 
        python_callable=extract_all)

    extract_one_task = PythonOperator(
        task_id="extract_one", 
        python_callable=extract_one)

    create_schemes = PostgresOperator(
        task_id="create_schemes",
        postgres_conn_id=os.environ['POSTGRES_DB'],
        sql="schemes.sql",
        split_statements=True,
    )

    create_tables = PostgresOperator(
        task_id="create_tables",
        postgres_conn_id=os.environ['POSTGRES_DB'],
        sql="raw_scheme.sql",
        split_statements=True,
    )

    load_expense = PythonOperator(
        task_id="load_expense",
        python_callable=load,
        op_kwargs={"kind": "расход"},
    )

    load_income = PythonOperator(
        task_id="load_income",
        python_callable=load,
        op_kwargs={"kind": "доход"},
    )

    extract_all_task >> extract_one_task >> create_schemes >> create_tables
    create_tables >> [load_expense, load_income]