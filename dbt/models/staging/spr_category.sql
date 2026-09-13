{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='category',
    pre_hook="truncate table {{ this }}"
) }}

with categories as (
    select trim(category) as category
    from {{ source('raw', 'expense') }}
    where category is not null
      and category not like '%,%'
      and category ~ '^[А-ЯA-Z]'
    group by trim(category)
    having count(*) > 1

    union

    select trim(category) as category
    from {{ source('raw', 'income') }}
    where category is not null
      and category not like '%,%'
      and category ~ '^[А-ЯA-Z]'
    group by trim(category)
    having count(*) > 1
)
select
    row_number() over (order by category) as category_id,
    category
from categories
