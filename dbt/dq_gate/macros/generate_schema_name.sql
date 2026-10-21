{#
  Schema naming:
    prod target   -> the custom schema as written (STAGING, MARTS)
    other targets -> <target schema>_<custom schema>, so every developer and every pull
                     request gets its own isolated pair of schemas.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'prod' -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
