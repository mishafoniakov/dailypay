{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='envelope',
    pre_hook="truncate table {{ this }}"
) }}

with envelopes as (
    select trim(envelope) as envelope
    from {{ source('raw', 'expense') }}
    where envelope is not null
      and envelope not like '%,%'
    group by trim(envelope)
    having count(*) > 1

    union

    select trim(envelope) as envelope
    from {{ source('raw', 'income') }}
    where envelope is not null
      and envelope not like '%,%'
    group by trim(envelope)
    having count(*) > 1
)
select
    row_number() over (order by envelope) as envelope_id,
    envelope
from envelopes
