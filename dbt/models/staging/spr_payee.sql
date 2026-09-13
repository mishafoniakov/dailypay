{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='payee',
    pre_hook="truncate table {{ this }}"
) }}

with payees as (
    select trim(payee) as payee
    from {{ source('raw', 'expense') }}
    where payee is not null
      and payee not like '%,%'
    group by trim(payee)
    having count(*) > 1

    union

    select trim(payee) as payee
    from {{ source('raw', 'income') }}
    where payee is not null
      and payee not like '%,%'
    group by trim(payee)
    having count(*) > 1
)
select
    row_number() over (order by payee) as payee_id,
    payee
from payees
