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
import json

from newrelic_lambda_cli.cliutils import failure, success


class NRGQL_APM(object):
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

    def get_entity_guids_from_entity_name(self, entity_name) -> dict[str, str]:
        entity_dicts = {}
        res = self.query(
            f"""
        query {{
        actor {{
            entitySearch(query: "name LIKE '{entity_name}' AND accountId = {self.account_id}") {{
            results {{
                entities {{
                guid
                name
                type
                }}
            }}
            }}
        }}
        }}
        """
        )

        try:
            data = res
            entities = data["actor"]["entitySearch"]["results"]["entities"]
            for entity in entities:
                if entity["name"] == entity_name:
                    entity_dicts[entity["type"]] = entity["guid"]
            return entity_dicts
        except (KeyError, TypeError) as e:
            print(f"An error occurred parsing the response: {e}")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def get_entity_alert_details(self, entity_guid) -> dict:
        res = self.query(
            f"""
        query {{
            actor {{
                entity(guid: "{entity_guid}") {{
                name
                guid
                reporting
                alertSeverity
                }}
                account(id: {self.account_id}) {{
                alerts {{
                    nrqlConditionsSearch(searchCriteria: {{queryLike: "{entity_guid}"}}) {{
                    nrqlConditions {{
                        id
                        name
                        enabled
                        description
                        policyId
                        nrql {{
                        query
                        }}
                        terms {{
                        operator
                        priority
                        threshold
                        thresholdDuration
                        thresholdOccurrences
                        }}
                    }}
                    }}
                }}
                }}
            }}
        }}
        """
        )

        print(f"Querying alert details for Lambda entity")

        try:
            data = res
            # Check for GraphQL errors in the response
            if "errors" in data:
                print("Error in GraphQL response:")
                for error in data["errors"]:
                    print(f"- {error.get('message')}")
                return None

            # Extract the entity data from the response
            actor_data = data.get("actor", {})
            entity_data = actor_data.get("entity")

            if not entity_data:
                print(f"Error: Could not find data for entity with GUID: {entity_guid}")
                return None

            # Extract alert conditions from the new path and add them to our entity_data dictionary
            conditions_search_result = (
                actor_data.get("account", {})
                .get("alerts", {})
                .get("nrqlConditionsSearch", {})
            )
            entity_data["alertConditions"] = (
                conditions_search_result.get("nrqlConditions", [])
                if conditions_search_result
                else []
            )

            return entity_data

        except (KeyError, TypeError) as e:
            print(f"An error occurred parsing the response: {e}")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def create_alert_for_new_entity(
        self, lambda_entity_selected_alerts, lambda_entity_guid, apm_entity_guid
    ):
        # Create a list of new NRQL conditions with modified queries
        new_nrql_conditions = []
        for alert_condition in lambda_entity_selected_alerts:
            original_description = alert_condition.get("description") or ""
            new_description = (
                f"{original_description} migrated from Lambda entity".strip()
            )
            alert_query = alert_condition["nrql"]["query"]
            alert_query = create_apm_alert_query(
                alert_query, lambda_entity_guid, apm_entity_guid
            )
            new_condition = {
                "name": alert_condition["name"] + " - apm_migrated",
                "description": new_description,
                "enabled": True,
                "nrql": {"query": alert_query},
                "terms": alert_condition["terms"],
            }
            policy_id = alert_condition.get("policyId")
            new_nrql_conditions.append((new_condition, policy_id))

        # Process each condition individually
        results = []
        for new_condition, policy_id in new_nrql_conditions:
            # Validate policy_id
            try:
                policy_id_int = int(policy_id)
            except (ValueError, TypeError):
                print(
                    f"Error: Invalid policy ID '{policy_id}' for condition '{new_condition['name']}'. Skipping."
                )
                continue

            # Format terms as proper GraphQL objects
            terms_list = []
            for term in new_condition["terms"]:
                term_str = "{"
                term_str += f"operator: {term['operator']}, "
                term_str += f"priority: {term['priority']}, "
                term_str += f"threshold: {term['threshold']}, "
                term_str += f"thresholdDuration: {term['thresholdDuration']}, "
                term_str += f"thresholdOccurrences: {term['thresholdOccurrences']}"
                term_str += "}"
                terms_list.append(term_str)

            terms_str = "[" + ", ".join(terms_list) + "]"

            mutation = f"""
            mutation {{
                alertsNrqlConditionStaticCreate(
                    accountId: {self.account_id}, 
                    condition: {{
                        name: "{new_condition['name']}"
                        description: "{new_condition['description']}"
                        enabled: {str(new_condition['enabled']).lower()}
                        nrql: {{
                            query: "{new_condition['nrql']['query']}"
                        }}
                        terms: {terms_str}
                    }}, 
                    policyId: "{policy_id_int}"
                ) {{
                    id
                    name
                    description
                    nrql {{
                        query
                    }}
                    terms {{
                        operator
                        priority
                        threshold
                        thresholdDuration
                        thresholdOccurrences
                    }}
                }}
            }}
            """

            try:
                res = self.query(mutation)
                # Check for GraphQL errors in the response
                if "errors" in res:
                    print("Error in GraphQL response:")
                    for error in res["errors"]:
                        print(f"- {error.get('message')}")
                    continue

                result = res["alertsNrqlConditionStaticCreate"]
                results.append(result)
                success(f"Successfully migrated to alert: {result['name']}")

            except (KeyError, TypeError) as e:
                print(f"An error occurred parsing the response: {e}")
                continue
            except Exception as e:
                print(f"An error occurred: {e}")
                continue

        return results


lambda_entity_alert_metric = {
    "cwBilledDuration": "apm.lambda.transaction.billed_duration",
    "cwDuration": "apm.lambda.transaction.duration",
    "cwInitDuration": "apm.lambda.transaction.init_duration",
    "cwMaxMemoryUsed": "apm.lambda.transaction.max_memory_used",
    "cwMemorySize": "apm.lambda.transaction.memory_size",
    "cloudWatchBilledDuration": "apm.lambda.transaction.billed_duration",
    "cloudWatchDuration": "apm.lambda.transaction.duration",
    "cloudWatchInitDuration": "apm.lambda.transaction.init_duration",
}


def select_lambda_entity_impacted_alerts(entity_data):
    if not entity_data or "alertConditions" not in entity_data:
        print("No alert conditions found.")
        return []

    selected_alerts = []
    alert_conditions = entity_data["alertConditions"]
    for condition in alert_conditions:
        alert_query = condition["nrql"]["query"]
        has_lambda_invocation = "AwsLambdaInvocation" in alert_query
        has_cloudwatch_metrics = any(
            metric in alert_query for metric in lambda_entity_alert_metric.keys()
        )
        if has_lambda_invocation and has_cloudwatch_metrics:
            print(f"Selected alert for migration: {condition['name']}")
            selected_alerts.append(condition)

    return selected_alerts


def create_apm_alert_query(alert_query, lambda_entity_guid, apm_entity_guid):
    for key, value in lambda_entity_alert_metric.items():
        if key in alert_query:
            alert_query = alert_query.replace(key, value)
            break
    apm_alert_query = alert_query.replace("AwsLambdaInvocation", "Metric")
    apm_alert_query = apm_alert_query.replace(lambda_entity_guid, apm_entity_guid)
    return apm_alert_query
