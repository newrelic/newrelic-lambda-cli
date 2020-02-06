from __future__ import absolute_import

import boto3
from moto import mock_cloudformation

from newrelic_lambda_cli.integrations import (
    check_for_ingest_stack,
    create_log_ingestion_function,
    get_cf_stack_status,
    remove_log_ingestion_function,
)


@mock_cloudformation
def test_check_for_ingest_stack(aws_credentials):
    """
    Asserts that check_for_ingestion_stack returns the ingestion stack if present;
    None if not.
    """
    session = boto3.Session(region_name="us-east-1")
    assert check_for_ingest_stack(session) is None

    create_log_ingestion_function(session, "mock-nr-license-key")
    assert check_for_ingest_stack(session) == "CREATE_COMPLETE"

    remove_log_ingestion_function(session)
    assert check_for_ingest_stack(session) is None


@mock_cloudformation
def test_get_cf_stack_status(aws_credentials):
    session = boto3.Session(region_name="us-east-1")
    assert get_cf_stack_status(session, "foo-bar-baz") is None
