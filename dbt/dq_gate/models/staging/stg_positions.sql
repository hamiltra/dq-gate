select
    cast(portfolio_id as varchar)     as portfolio_id,
    cast(security_id as varchar)      as security_id,
    cast(as_of_date as date)          as as_of_date,
    cast(quantity as numeric(18, 2))  as quantity,
    loaded_at
from {{ source('raw', 'positions') }}
