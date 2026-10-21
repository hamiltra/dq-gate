-- Singular test: fails if any closing price is zero or negative.
select security_id, price_date, close_price
from {{ ref('stg_daily_prices') }}
where close_price <= 0
