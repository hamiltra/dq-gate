select
    portfolio_id,
    as_of_date,
    count(*)            as position_count,
    sum(market_value)   as total_market_value
from {{ ref('fct_position_valuation') }}
group by portfolio_id, as_of_date
