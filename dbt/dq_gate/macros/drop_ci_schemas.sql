{#
  Removes the schemas a CI run created. Refuses to run on any target except 'ci'.
  Usage: dbt run-operation drop_ci_schemas --target ci
#}
{% macro drop_ci_schemas() %}
    {% if target.name != 'ci' %}
        {{ exceptions.raise_compiler_error("drop_ci_schemas only runs on the 'ci' target") }}
    {% endif %}
    {% for suffix in ['staging', 'marts'] %}
        {% do run_query('drop schema if exists ' ~ target.database ~ '.' ~ target.schema ~ '_' ~ suffix ~ ' cascade') %}
        {% do log('Dropped schema ' ~ target.schema ~ '_' ~ suffix, info=true) %}
    {% endfor %}
    {% do run_query('drop schema if exists ' ~ target.database ~ '.' ~ target.schema ~ ' cascade') %}
{% endmacro %}
