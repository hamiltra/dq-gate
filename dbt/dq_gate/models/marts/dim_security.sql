with price_range as (
    select
        security_id,
        min(price_date) as first_price_date,
        max(price_date) as last_price_date
    from {{ ref('stg_daily_prices') }}
    group by security_id
)

select
    s.security_id,
    s.ticker,
    s.security_name,
    s.asset_class,
    s.sector,
    s.currency,
    s.issue_date,
    p.first_price_date,
    p.last_price_date
from {{ ref('stg_securities') }} as s
left join price_range as p
    on s.security_id = p.security_id
