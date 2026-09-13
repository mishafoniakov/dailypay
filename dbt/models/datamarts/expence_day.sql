{{ config(materialized='view') }}

select
    txn_date,
    sum(amount) as amount
from
    {{ ref('stg_expense') }}
group by
    txn_date
order by
    1 asc,
    2 asc