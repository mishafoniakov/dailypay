{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key=['txn_date', 'payee_id', 'category_id', 'envelope_id', 'amount'],
    alias='expense',
    pre_hook="truncate table {{ this }}"
) }}

with expense as 
    (select
        txn_date,
        payee,
        split_part(category, ', ', 1) as category,
        envelope,
        amount
    from 
        {{ source('raw', 'expense') }})
select
    txn_date,
    payee.payee_id as payee_id,
    cat.category_id as category_id,
    env.envelope_id as envelope_id,
    amount
from
    expense as exp
left join
    {{ ref('spr_category') }} as cat on exp.category = cat.category
left join
    {{ ref('spr_envelope') }} as env on exp.envelope = env.envelope
left join
    {{ ref('spr_payee') }} as payee on exp.payee = payee.payee
