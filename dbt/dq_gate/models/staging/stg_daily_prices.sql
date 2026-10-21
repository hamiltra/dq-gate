select
    cast(security_id as varchar)         as security_id,
    cast(price_date as date)             as price_date,
    cast(close_price as numeric(18, 4))  as close_price,
    cast(volume as bigint)               as volume,
    loaded_at
from {{ source('raw', 'daily_prices') }}
