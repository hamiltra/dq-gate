-- Singular test: every position must have a closing price on its as-of date.
select portfolio_id, security_id, as_of_date
from {{ ref('fct_position_valuation') }}
where close_price is null
