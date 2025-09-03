from collections import namedtuple

INTEGRATION_INSTALL_KEYS = [
    "session",
    "verbose",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "aws_role_policy",
    "enable_logs",
    "stackname",
    "memory_size",
    "linked_account_name",
    "nr_account_id",
    "nr_api_key",
    "nr_region",
    "timeout",
    "role_name",
    "enable_license_key_secret",
    "enable_cw_ingest",
    "integration_arn",
    "tags",
]

INTEGRATION_UNINSTALL_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "stackname",
    "nr_account_id",
    "force",
]

INTEGRATION_UPDATE_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "enable_logs",
    "stackname",
    "memory_size",
    "nr_account_id",
    "nr_api_key",
    "nr_region",
    "timeout",
    "role_name",
    "enable_license_key_secret",
    "tags",
]

OTEL_INGESTION_INSTALL_KEYS = [
    "session",
    "verbose",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "aws_role_policy",
    "stackname",
    "memory_size",
    "nr_account_id",
    "nr_api_key",
    "nr_region",
    "timeout",
    "role_name",
    "tags",
]

OTEL_INGESTION_UNINSTALL_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "stackname",
    "nr_account_id",
    "force",
]

OTEL_INGESTION_UPDATE_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "stackname",
    "memory_size",
    "nr_account_id",
    "nr_api_key",
    "nr_region",
    "timeout",
    "role_name",
    "tags",
]

LAYER_INSTALL_KEYS = [
    "session",
    "verbose",
    "nr_account_id",
    "nr_api_key",
    "nr_ingest_key",
    "nr_region",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "functions",
    "excludes",
    "layer_arn",
    "upgrade",
    "apm",
    "enable_extension",
    "enable_extension_function_logs",
    "disable_extension_function_logs",
    "nr_tags",
    "nr_env_delimiter",
    "send_function_logs",
    "disable_function_logs",
    "send_extension_logs",
    "disable_extension_logs",
    "java_handler_method",
    "esm",
]

LAYER_UNINSTALL_KEYS = [
    "session",
    "verbose",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "functions",
    "excludes",
]

SUBSCRIPTION_INSTALL_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "functions",
    "stackname",
    "excludes",
    "filter_pattern",
    "otel",
]

ALERTS_MIGRATE_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "nr_account_id",
    "nr_api_key",
    "nr_region",
    "function",
    "excludes",
    "verbose",
]

SUBSCRIPTION_UNINSTALL_KEYS = [
    "session",
    "aws_profile",
    "aws_region",
    "aws_permissions_check",
    "functions",
    "excludes",
    "otel",
]


IntegrationInstall = namedtuple("IntegrationInstall", INTEGRATION_INSTALL_KEYS)
IntegrationUninstall = namedtuple("IntegrationUninstall", INTEGRATION_UNINSTALL_KEYS)
IntegrationUpdate = namedtuple("IntegrationUpdate", INTEGRATION_UPDATE_KEYS)

OtelIngestionInstall = namedtuple("OtelIngestionInstall", OTEL_INGESTION_INSTALL_KEYS)
OtelIngestionUninstall = namedtuple(
    "OtelIngestionUninstall", OTEL_INGESTION_UNINSTALL_KEYS
)
OtelIngestionUpdate = namedtuple("OtelIngestionUpdate", OTEL_INGESTION_UPDATE_KEYS)


LayerInstall = namedtuple("LayerInstall", LAYER_INSTALL_KEYS)
LayerUninstall = namedtuple("LayerUninstall", LAYER_UNINSTALL_KEYS)

AlertsMigrate = namedtuple("AlertsMigrate", ALERTS_MIGRATE_KEYS)

SubscriptionInstall = namedtuple("SubscriptionInstall", SUBSCRIPTION_INSTALL_KEYS)
SubscriptionUninstall = namedtuple("SubscriptionUninstall", SUBSCRIPTION_UNINSTALL_KEYS)
