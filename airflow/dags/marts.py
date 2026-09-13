from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="datamarts",
    schedule=None,
    is_paused_upon_creation=False,
) as dag:

    BashOperator(
        task_id="dbt_datamarts",
        bash_command="dbt run --project-dir /opt/dbt --profiles-dir /opt/dbt --select expence_day expence_month income_month",
        cwd="/opt/dbt",
    )
