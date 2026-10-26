-- M4 one-time grants. Run in a Snowsight worksheet with "Run All".
-- Needs ACCOUNTADMIN. Contains no secrets.

USE ROLE ACCOUNTADMIN;

-- Lets DQ_CI_ROLE attach data metric functions to tables and schedule them
GRANT EXECUTE DATA METRIC FUNCTION ON ACCOUNT TO ROLE DQ_CI_ROLE;

-- Lets DQ_CI_ROLE read the results Snowflake records for attached functions
GRANT APPLICATION ROLE SNOWFLAKE.DATA_QUALITY_MONITORING_VIEWER TO ROLE DQ_CI_ROLE;

-- Lets DQ_CI_ROLE create the custom function in DQ_AUDIT (it may already be covered by ALL)
GRANT CREATE DATA METRIC FUNCTION ON SCHEMA DQ_DEMO.DQ_AUDIT TO ROLE DQ_CI_ROLE;

-- Check: expect the three new grants in the output
SHOW GRANTS TO ROLE DQ_CI_ROLE;
