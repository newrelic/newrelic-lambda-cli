# -*- coding: utf-8 -*-

"""

Example usage:

    >>> from newrelic_lambda_cli.api import NewRelicGQL
    >>> gql = NewRelicGQL("api key here", "account id here")
    >>> gql.get_linked_accounts()

"""

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

import click
import requests

from newrelic_lambda_cli.cliutils import failure, success
from newrelic_lambda_cli.types import (
    IntegrationInstall,
    IntegrationUpdate,
    LayerInstall,
    OtelIngestionInstall,
    OtelIngestionUninstall,
    OtelIngestionUpdate,
)
from newrelic_lambda_cli.utils import parse_arn

__cached_license_key = None


class NewRelicGQL(object):
    def __init__(self, account_id, api_key, region="us"):
        try:
            self.account_id = int(account_id)
        except ValueError:
            raise ValueError("Account ID must be an integer")

        self.api_key = api_key

        if region == "us":
            self.url = "https://api.newrelic.com/graphql"
        elif region == "eu":
            self.url = "https://api.eu.newrelic.com/graphql"
        elif region == "staging":
            self.url = "https://staging-api.newrelic.com/graphql"
        else:
            raise ValueError("Region must be one of 'us' or 'eu'")

        transport = RequestsHTTPTransport(url=self.url, use_json=True)
        transport.headers = {"api-key": self.api_key}

        try:
            self.client = Client(transport=transport, fetch_schema_from_transport=True)
        except Exception:
            self.client = Client(transport=transport, fetch_schema_from_transport=False)

    def query(self, query, timeout=None, **variable_values):
        return self.client.execute(
            gql(query), timeout=timeout, variable_values=variable_values or None
        )

    def get_linked_accounts(self):
        """
        return a list of linked accounts for the New Relic account
        """
        res = self.query(
            """
            query ($accountId: Int!) {
              actor {
                account(id: $accountId) {
                  cloud {
                    linkedAccounts {
                      id
                      name
                      authLabel
                      externalId
                      metricCollectionMode
                    }
                  }
                }
              }
            }
            """,
            accountId=self.account_id,
        )
        try:
            return res["actor"]["account"]["cloud"]["linkedAccounts"]
        except KeyError:
            return []

    def get_license_key(self):
        """
        Fetch the license key for the NR Account
        """
        res = self.query(
            """
            query ($accountId: Int!) {
              requestContext {
                apiKey
              }
              actor {
                account(id: $accountId) {
                  licenseKey
                  id
                  name
                }
              }
            }
            """,
            accountId=self.account_id,
        )
        try:
            return res["actor"]["account"]["licenseKey"]
        except KeyError:
            return None

    def get_linked_account_by_id(self, id):
        """
        return a specific linked account of the New Relic account by ID
        """
        accounts = self.get_linked_accounts()
        try:
            return next((a for a in accounts if a["id"] == int(id)), None)
        except KeyError:
            return None

    def get_linked_account_by_external_id(self, external_id):
        """
        return a specific linked account of the New Relic account by External ID
        """
        accounts = self.get_linked_accounts()
        try:
            return next((a for a in accounts if a["externalId"] == external_id), None)
        except KeyError:
            return None

    def link_account(self, role_arn, account_name):
        """
        create a linked account (cloud integrations account)
        in the New Relic account
        """
        res = self.query(
            """
            mutation ($accountId: Int!, $accounts: CloudLinkCloudAccountsInput!) {
              cloudLinkAccount (accountId: $accountId, accounts: $accounts) {
                linkedAccounts {
                  id
                  name
                  authLabel
                  externalId
                }
                errors {
                    message
                }
              }
            }
            """,
            accountId=self.account_id,
            accounts={"aws": {"arn": role_arn, "name": account_name}},
        )
        try:
            return res["cloudLinkAccount"]["linkedAccounts"][0]
        except (IndexError, KeyError):
            if "errors" in res["cloudLinkAccount"]:
                failure(
                    "Error while linking account with New Relic:\n%s"
                    % "\n".join(
                        [
                            e["message"]
                            for e in res["cloudLinkAccount"]["errors"]
                            if "message" in e
                        ]
                    )
                )
            return None

    def unlink_account(self, linked_account_id):
        """
        Unlink a New Relic Cloud integrations account
        """
        res = self.query(
            """
            mutation ($accountId: Int!, $accounts: [CloudUnlinkAccountsInput!]!) {
              cloudUnlinkAccount (accountId: $accountId, accounts: $accounts) {
                unlinkedAccounts {
                  id
                  name
                }
                errors {
                  type
                  message
                }
              }
            }
            """,
            accountId=self.account_id,
            accounts=[{"linkedAccountId": linked_account_id}],
        )
        if "errors" in res and res["errors"]:
            failure(
                "Error while unlinking account with New Relic:\n%s"
                % "\n".join([e["message"] for e in res["errors"] if "message" in e])
            )
        return res

    def get_integrations(self, linked_account_id):
        """
        returns the integrations for the linked account
        """
        res = self.query(
            """
            query ($accountId: Int!, $linkedAccountId: Int!) {
              actor {
                account (id: $accountId) {
                  cloud {
                    linkedAccount(id: $linkedAccountId) {
                      integrations {
                        id
                        name
                        createdAt
                        updatedAt
                        service {
                          slug
                          isEnabled
                        }
                      }
                    }
                  }
                }
              }
            }
            """,
            accountId=self.account_id,
            linkedAccountId=int(linked_account_id),
        )
        try:
            return res["actor"]["account"]["cloud"]["linkedAccount"]["integrations"]
        except KeyError:
            return []

    def get_integration_by_service_slug(self, linked_account_id, service_slug):
        integrations = self.get_integrations(linked_account_id)
        try:
            return next(
                (i for i in integrations if i["service"]["slug"] == service_slug), None
            )
        except KeyError:
            return None

    def is_integration_enabled(self, linked_account_id, service_slug):
        integration = self.get_integration_by_service_slug(
            linked_account_id, service_slug
        )
        try:
            return integration and integration["service"]["isEnabled"]
        except KeyError:
            return False

    def enable_integration(self, linked_account_id, provider_slug, service_slug):
        """
        enable monitoring of a Cloud provider service (integration)
        """
        res = self.query(
            """
            mutation ($accountId: Int!, $integrations: CloudIntegrationsInput!) {
              cloudConfigureIntegration (
                accountId: $accountId,
                integrations: $integrations
              ) {
                integrations {
                  id
                  name
                  service {
                    id
                    name
                  }
                }
                errors {
                  linkedAccountId
                  message
                }
              }
            }
            """,
            accountId=self.account_id,
            integrations={
                provider_slug: {service_slug: [{"linkedAccountId": linked_account_id}]}
            },
        )
        try:
            return res["cloudConfigureIntegration"]["integrations"][0]
        except (IndexError, KeyError):
            if "errors" in res:
                failure(
                    "Error while enabling integration with New Relic:\n%s"
                    % "\n".join([e["message"] for e in res["errors"] if "message" in e])
                )
            return None

    def disable_integration(self, linked_account_id, provider_slug, service_slug):
        """
        Disable monitoring of a Cloud provider service (integration)
        """
        res = self.query(
            """
            mutation ($accountId: Int!, $integrations: CloudIntegrationsInput!) {
              cloudDisableIntegration (
                accountId: $accountId,
                integrations: $integrations
              ) {
                disabledIntegrations {
                  id
                  accountId
                  name
                }
                errors {
                  type
                  message
                }
              }
            }
            """,
            accountId=self.account_id,
            integrations={
                provider_slug: {service_slug: [{"linkedAccountId": linked_account_id}]}
            },
        )
        if "errors" in res:
            failure(
                "Error while disabling integration with New Relic:\n%s"
                % "\n".join([e["message"] for e in res["errors"] if "message" in e])
            )
        return res


def validate_gql_credentials(input):

    assert isinstance(
        input,
        (
            IntegrationInstall,
            IntegrationUpdate,
            LayerInstall,
            OtelIngestionInstall,
            OtelIngestionUpdate,
        ),
    )

    try:
        return NewRelicGQL(input.nr_account_id, input.nr_api_key, input.nr_region)
    except requests.exceptions.HTTPError:
        raise click.BadParameter(
            "Could not authenticate with New Relic. Check that your New Relic Account "
            "ID and API Key are valid and try again.",
            ctx=None,
            param="nr_api_key",
            param_hint="New Relic User API Key",
        )


def retrieve_license_key(gql):
    global __cached_license_key
    if __cached_license_key:
        return __cached_license_key
    assert isinstance(gql, NewRelicGQL)
    try:
        __cached_license_key = gql.get_license_key()
        return __cached_license_key
    except Exception:
        raise click.BadParameter(
            f"For New Relic Account ID: {gql.account_id}. "
            "Could not retrieve INGEST - LICENSE key from New Relic. "
            "Check that your New Relic Account ID and USER key are valid and try again.",
            ctx=None,
            param="nr_api_key",
            param_hint="API Key",
        )


def create_integration_account(gql, input, role):
    """
    Creates a New Relic Cloud integration account for the specified AWS IAM role.
    """
    assert isinstance(gql, NewRelicGQL)
    assert isinstance(input, IntegrationInstall)
    role_arn = role["Role"]["Arn"]
    external_id = parse_arn(role_arn)["account"]
    account = gql.get_linked_account_by_external_id(external_id)
    if account:
        success(
            "Cloud integrations account [%s] already exists "
            "in New Relic account [%d] with IAM role [%s]."
            % (account["name"], input.nr_account_id, account["authLabel"])
        )
        return account
    account = account = gql.link_account(role_arn, input.linked_account_name)
    if account:
        success(
            "Cloud integrations account [%s] was created in New Relic account [%s] "
            "with IAM role [%s]."
            % (input.linked_account_name, input.nr_account_id, role_arn)
        )
        return account
    failure(
        "Could not create Cloud integrations account [%s] in New Relic account [%s] "
        "with role [%s]. This may be due to a previously installed integration. "
        "Please contact New Relic support for assistance."
        % (input.linked_account_name, input.nr_account_id, role_arn)
    )


def enable_lambda_integration(gql, input, linked_account_id):
    """
    Enables AWS Lambda for the specified New Relic Cloud integrations account.

    Returns True for success and False for failure.
    """
    assert isinstance(gql, NewRelicGQL)
    assert isinstance(input, IntegrationInstall)
    account = gql.get_linked_account_by_id(linked_account_id)
    if account is None:
        failure(
            "Could not find Cloud integrations account "
            "[%d] in New Relic account [%d]." % (linked_account_id, input.nr_account_id)
        )
        return False

    metric_collection_mode = account["metricCollectionMode"]

    if metric_collection_mode == "PUSH":
        success(
            "Cloud integrations account [%s] is using CloudWatch Metric Streams"
            % (input.nr_account_id)
        )
        return True

    is_lambda_enabled = gql.is_integration_enabled(linked_account_id, "lambda")
    if is_lambda_enabled:
        success(
            "The AWS Lambda integration is already enabled in "
            "Cloud integrations account [%s] of New Relic account [%d]."
            % (account["name"], input.nr_account_id)
        )
        return True
    try:
        integration = gql.enable_integration(linked_account_id, "aws", "lambda")
    except Exception:
        failure(
            "Could not enable New Relic AWS Lambda integration for Cloud integrations "
            "account [%s] in New Relic account [%d]. Please contact New Relic Support "
            "for assistance." % (account["name"], input.nr_account_id)
        )
        return False
    if integration:
        success(
            "Integration [id=%s, name=%s] has been enabled in Cloud "
            "integrations account [%s] of New Relic account [%d]."
            % (
                integration["id"],
                integration["name"],
                account["name"],
                input.nr_account_id,
            )
        )
        return True
    failure(
        "Something went wrong while enabling the New Relic AWS Lambda integration. "
        "Please contact New Relic support for further assistance."
    )
    return False
