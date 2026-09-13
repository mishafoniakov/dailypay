import os

from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="trans",
    schedule=None,
    template_searchpath=["/data"],
) as dag:

    create_tables = PostgresOperator(
        task_id="create_tables",
        postgres_conn_id=os.environ['POSTGRES_DB'],
        sql="stage_scheme.sql",
        split_statements=True,
    )

    create_keys = PostgresOperator(
        task_id="create_keys",
        postgres_conn_id=os.environ['POSTGRES_DB'],
        sql="stage_keys.sql",
        split_statements=True,
    )

    deps = BashOperator(
        task_id="dbt_deps",
        bash_command=(
            "if [ -d /opt/dbt/dbt_packages/dbt_utils ] && [ -d /opt/dbt/dbt_packages/dbt_expectations ]; then "
            "echo 'dbt packages already installed'; "
            "else dbt deps --project-dir /opt/dbt --profiles-dir /opt/dbt; fi"
        ),
        cwd="/opt/dbt",
    )

    create_spr = BashOperator(
        task_id="dbt_create_spr",
        bash_command="dbt run --project-dir /opt/dbt --profiles-dir /opt/dbt --select spr_category spr_envelope spr_payee",
        cwd="/opt/dbt",
    )

    create_tab = BashOperator(
        task_id="dbt_create_tab",
        bash_command="dbt run --project-dir /opt/dbt --profiles-dir /opt/dbt --select stg_income stg_expense",
        cwd="/opt/dbt",
    )

    create_tables >> create_keys >> deps >> create_spr >> create_tab
