# TC Account Inventory

Tencent Cloud account-wide resource inventory generator. Runs as an **SCF (Serverless Cloud Function)** that discovers all resources across all regions via the **Tag API**, enriches them with service-specific details, and outputs a CSV file.

## How It Works

1. **Region Discovery** — Fetches all available regions via CVM `DescribeRegions`
2. **Resource Discovery** — Calls Tag `GetResources` per region (+ global) to enumerate all resources (tagged and untagged)
3. **Enrichment** — For supported services, calls Describe APIs to get resource type, payment model, status, and name
4. **Output** — Generates a CSV and writes to `/tmp` (+ optional COS upload)

## CSV Output Columns

| Column | Description |
|---|---|
| Region | Tencent Cloud region (e.g. `ap-singapore`) |
| ServiceType | Service identifier (e.g. `cvm`, `cbs`, `clb`) |
| ResourcePrefix | Resource prefix from six-segment ARN |
| ResourceId | Unique resource ID |
| ResourceName | Resource name (from enrichment) |
| ResourceType | Instance/disk/LB type (from enrichment) |
| PaymentModel | `PREPAID`, `POSTPAID_BY_HOUR`, etc. |
| Status | Resource status |
| Tags | Semicolon-separated `key=value` pairs |
| ResourceArn | Full six-segment resource ARN |

## Services In Scope

### Discovery (Tag API — all resources)

The Tag `GetResources` API returns **all** resources across all services that support tagging. This includes but is not limited to:

| Category | Service | ServiceType | Resource Prefix |
|---|---|---|---|
| **Compute** | Cloud Virtual Machine | `cvm` | `instance` |
| | Lighthouse | `lighthouse` | `instance` |
| | Serverless Cloud Function | `scf` | `function` |
| | Tencent Kubernetes Engine | `tke` | `cluster` |
| | Elastic Microservice | `tem` | `environment` |
| **Storage** | Cloud Block Storage | `cbs` | `disk` |
| | Cloud Object Storage | `cos` | `bucket` |
| **Network** | Virtual Private Cloud | `vpc` | `vpc`, `subnet`, `eip`, `natGateway`, `vpngw` |
| | Cloud Connect Network | `ccn` | `ccn` |
| | Cloud Load Balancer | `clb` | `lb` |
| | Global Accelerator | `gaap` | `group` |
| **Databases** | TencentDB for MySQL | `cdb` | `instanceId` |
| | TencentDB for PostgreSQL | `postgres` | `DBInstanceId` |
| | TencentDB for SQL Server | `sqlserver` | `instance` |
| | TDSQL (Distributed) | `dcdb` | `instance` |
| | TDSQL-C (CynosDB) | `cynosdb` | `instance` |
| | TencentDB for Redis | `redis` | `instance` |
| | TencentDB for MongoDB | `mongodb` | `instance` |
| **Messaging** | CKafka | `ckafka` | `instance` |
| | TDMQ (Pulsar/RocketMQ/RabbitMQ) | `tdmq` | `cluster` |
| **Search & Analytics** | Elasticsearch Service | `es` | `instance` |
| | EMR | `emr` | `emr-instance` |
| | Cloud Log Service | `cls` | `topic` |
| | Data Lake Compute | `dlc` | `dataEngine` |
| | WeData | `wedata` | `workspace` |
| **Security** | Anti-DDoS Advanced | `antiddos` | `bgpip` |
| | Cloud Firewall | `cfw` | `firewall` |
| | KMS | `kms` | `key` |
| | Secrets Manager | `ssm` | `secret` |
| **Other** | Container Registry | `tcr` | `instance` |
| | Private DNS | `privatedns` | `zone` |
| | VOD | `vod` | `subAppId` |
| | CSS (Live Streaming) | `css` | `domain` |
| | Simple Email Service | `ses` | `email` |

### Enrichment (Detailed Describe APIs)

Currently implemented enrichers that fetch resource type, payment model, and status:

| Service | Enricher | API Used |
|---|---|---|
| CVM | `enrichers/cvm.py` | `DescribeInstances` |
| CBS | `enrichers/cbs.py` | `DescribeDisks` |
| CLB | `enrichers/clb.py` | `DescribeLoadBalancers` |
| MySQL (CDB) | `enrichers/mysql.py` | `DescribeDBInstances` |
| Redis | `enrichers/redis_enrich.py` | `DescribeInstances` |

All other services fall back to `enrichers/generic.py` — resources still appear in the CSV with their tags, but type/payment/status fields will be empty until a specific enricher is added.

## SCF Deployment

### Environment Variables (required)

| Variable | Description |
|---|---|
| `TENCENTCLOUD_SECRET_ID` | API SecretId |
| `TENCENTCLOUD_SECRET_KEY` | API SecretKey |
| `COS_BUCKET` | COS bucket name (e.g. `inventory-1250000000`) |
| `COS_REGION` | COS bucket region (e.g. `ap-singapore`) |
| `COS_KEY_PREFIX` | COS folder prefix (default: `inventory/`) |

### SCF Configuration

| Setting | Value |
|---|---|
| Runtime | Python 3.9+ |
| Handler | `inventory.main_handler` |
| Timeout | 900 seconds (max) |
| Memory | 256 MB (recommended) |
| Trigger | Timer (cron) — e.g. daily |

### First-time Deployment

Upload `deploy/tc-account-inventory.zip` as the SCF function code package.

### Subsequent Updates

Upload changed `.py` files directly via SCF console code editor — **do not rebuild the zip**.

## CAM Policy

The SCF execution role needs **read-only** access to all services being scanned. Minimum permissions:

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "tag:GetResources",
        "cvm:DescribeRegions",
        "cvm:DescribeInstances",
        "cbs:DescribeDisks",
        "clb:DescribeLoadBalancers",
        "cdb:DescribeDBInstances",
        "redis:DescribeInstances",
        "cos:PutObject"
      ],
      "resource": ["*"]
    }
  ]
}
```

## SCF Testing Checklist

### Pre-Deploy
- [ ] Set env vars in SCF console: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`, `COS_BUCKET`, `COS_REGION`
- [ ] CAM role attached to SCF with read-only permissions for Tag, CVM, CBS, CLB, CDB, Redis + COS PutObject
- [ ] Timeout set to **900s**, memory **256MB**
- [ ] Handler set to **`inventory.main_handler`**
- [ ] Runtime: **Python 3.9+**

### Smoke Test (SCF Console → Test)
- [ ] Invoke with empty `{}` event — should return `statusCode: 200`
- [ ] Check logs for `[*] Fetching regions...` — confirms auth works
- [ ] Check logs for region count (expect ~30 regions)
- [ ] Check logs for `[*] Scanning region: ...` — confirms Tag API access
- [ ] Verify no `[ERROR]` in output

### Validation
- [ ] Check `total_resources` in response > 0
- [ ] Check `/tmp/inventory.csv` exists (visible in logs)
- [ ] Spot-check a known resource ID appears in output
- [ ] Verify enriched fields (ResourceType, PaymentModel) populated for CVM/CBS/CLB
- [ ] Verify Tags column populated for tagged resources
- [ ] Verify untagged resources also appear (Tags column empty)

### Edge Cases
- [ ] Empty region (no resources) — should log `Found 0 resources` and continue
- [ ] Region with API throttling — should see `[WARN]` but not crash
- [ ] Global scan picks up COS buckets / CCN / PrivateDNS

### COS Upload
- [ ] `COS_BUCKET` set → file uploaded to `inventory/inventory_YYYYMMDD_HHMMSS.csv`
- [ ] `COS_BUCKET` empty → logs `[WARN] COS_BUCKET not set`, still succeeds with local output

### Performance
- [ ] Monitor execution time — should complete within 900s for typical accounts
- [ ] Check memory usage stays under 256MB
- [ ] If timeout occurs → consider splitting by region batches or increasing timeout

## Adding New Enrichers

1. Create `enrichers/newservice.py` with function `enrich_X(cred, region, resource_ids)` returning `{id: {ResourceType, PaymentModel, Status, Name}}`
2. Register in `enrichers/__init__.py`
3. Upload updated files via SCF code editor

## SDK Reference

- [tencentcloud-sdk-python-intl-en](https://github.com/TencentCloud/tencentcloud-sdk-python-intl-en/tree/master/tencentcloud)
