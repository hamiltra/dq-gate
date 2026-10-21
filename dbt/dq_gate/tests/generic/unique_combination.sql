{#
  Generic test: the listed columns must be unique together.
  Usage in YAML:
    data_tests:
      - unique_combination:
          columns: [portfolio_id, security_id, as_of_date]
#}
{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as row_count
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
