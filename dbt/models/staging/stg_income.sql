{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key=['txn_date', 'payee_id', 'category_id', 'envelope_id', 'amount'],
    alias='income',
    pre_hook="truncate table {{ this }}"
) }}

with income as 
    (select
        txn_date,
        payee,
        split_part(category, ', ', 1) as category,
        envelope,
        amount
    from 
        {{ source('raw', 'income') }})
select
    txn_date,
    payee.payee_id as payee_id,
    cat.category_id as category_id,
    env.envelope_id as envelope_id,
    amount
from
    income as inc
left join
    {{ ref('spr_category') }} as cat on inc.category = cat.category
left join
    {{ ref('spr_envelope') }} as env on inc.envelope = env.envelope
left join
    {{ ref('spr_payee') }} as payee on inc.payee = payee.payee

