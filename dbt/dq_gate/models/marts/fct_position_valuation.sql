-- One row per portfolio, security and date, valued at that day's closing price.
-- close_price is null (and market_value null) when no price exists for the date;
-- tests/assert_positions_have_prices.sql fails the build if that ever happens.
select
    pos.portfolio_id,
    pos.security_id,
    pos.as_of_date,
    pos.quantity,
    px.close_price,
    pos.quantity * px.close_price as market_value
from {{ ref('stg_positions') }} as pos
left join {{ ref('stg_daily_prices') }} as px
    on pos.security_id = px.security_id
    and pos.as_of_date = px.price_date
