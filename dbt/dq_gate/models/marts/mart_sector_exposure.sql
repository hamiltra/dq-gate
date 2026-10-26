-- Daily market value per portfolio and sector, with each sector's share of the portfolio.
with valued as (
    select
        v.portfolio_id,
        v.as_of_date,
        s.sector,
        v.market_value
    from {{ ref('fct_position_valuation') }} as v
    inner join {{ ref('dim_security') }} as s
        on v.security_id = s.security_id
),

by_sector as (
    select
        portfolio_id,
        as_of_date,
        sector,
        sum(market_value) as market_value
    from valued
    group by portfolio_id, as_of_date, sector
)

select
    portfolio_id,
    as_of_date,
    sector,
    market_value,
    market_value / sum(market_value) over (partition by portfolio_id, as_of_date)
        as portfolio_weight
from by_sector
