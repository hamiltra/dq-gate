-- Singular test: the summary mart must reconcile to the position-level fact (to the cent).
with detail as (
    select sum(market_value) as total from {{ ref('fct_position_valuation') }}
),
summary as (
    select sum(total_market_value) as total from {{ ref('mart_portfolio_summary') }}
)
select detail.total as detail_total, summary.total as summary_total
from detail
cross join summary
where abs(detail.total - summary.total) > 0.01
