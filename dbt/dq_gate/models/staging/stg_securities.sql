select
    cast(security_id as varchar)   as security_id,
    upper(trim(ticker))            as ticker,
    trim(security_name)            as security_name,
    upper(trim(asset_class))       as asset_class,
    trim(sector)                   as sector,
    upper(trim(currency))          as currency,
    cast(issue_date as date)       as issue_date,
    loaded_at
from {{ source('raw', 'securities') }}
