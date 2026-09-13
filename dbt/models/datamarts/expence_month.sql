{{ config(materialized='view') }}

select
    extract(year from txn_date) as txn_year,
    extract(month from txn_date) as txn_month,
    sum(amount) as amount
from
    {{ ref('stg_expense') }}
group by
    1, 2
order by
    1, 2