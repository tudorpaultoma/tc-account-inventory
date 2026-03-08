import os

# Auth — credentials are read dynamically at call time in discovery.get_credentials()
# to ensure SCF-injected env vars are captured after cold start.

# COS output settings (set in SCF environment variables)
COS_BUCKET = os.environ.get("COS_BUCKET", "")           # e.g. "my-bucket-1250000000"
COS_REGION = os.environ.get("COS_REGION", "ap-singapore")
COS_KEY_PREFIX = os.environ.get("COS_KEY_PREFIX", "inventory/")  # folder in bucket

# Local temp output (SCF writable dir)
OUTPUT_DIR = "/tmp"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "inventory.csv")

# Pagination
TAG_PAGE_SIZE = 200  # max for GetResources

# Rate limiting
API_SLEEP = 0.1  # seconds between API calls

# Services to scan — maps ServiceType to list of resource prefixes
# Based on Tag API six-segment format: qcs::ServiceType:Region:Account:ResourcePrefix/ResourceId
SERVICE_RESOURCE_MAP = {
    "cvm": ["instance"],
    "cbs": ["disk"],
    "clb": ["lb"],
    "vpc": ["vpc", "subnet", "eip", "natGateway", "vpngw"],
    "ccn": ["ccn"],
    "scf": ["function"],
    "cos": ["bucket"],
    "cdb": ["instanceId"],        # MySQL
    "postgres": ["DBInstanceId"],
    "cynosdb": ["instance"],      # TDSQL-C
    "sqlserver": ["instance"],    # MSSQL
    "redis": ["instance"],
    "mongodb": ["instance"],
    "dcdb": ["instance"],         # TDSQL
    "es": ["instance"],           # Elasticsearch
    "emr": ["emr-instance"],
    "tke": ["cluster"],
    "cls": ["topic"],
    "ckafka": ["instance"],
    "tdmq": ["cluster"],
    "lighthouse": ["instance"],
    "tcr": ["instance"],
    "kms": ["key"],
    "ssm": ["secret"],
    "tem": ["environment"],
    "gaap": ["group"],
    "privatedns": ["zone"],
    "antiddos": ["bgpip"],
    "cfw": ["firewall"],
    "dlc": ["dataEngine"],
    "wedata": ["workspace"],
    "vod": ["subAppId"],
    "css": ["domain"],
    "ses": ["email"],
}

# Regions will be fetched dynamically via CVM DescribeRegions
