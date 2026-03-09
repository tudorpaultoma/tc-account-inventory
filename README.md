# TC Account Inventory

Tencent Cloud account-wide resource inventory generator. Runs as an **SCF (Serverless Cloud Function)** that discovers all resources across all regions via the **Tag API**, enriches them with service-specific details, and outputs a CSV file.

## Project Structure

```
index.py              — Main script (config, discovery, orchestration, COS upload, SCF handler)
enrichers/            — Per-service enrichment modules
  __init__.py         — Enricher registry & dispatch
  cvm.py, cbs.py, …  — Service-specific Describe API calls
  generic.py          — Fallback (no-op) enricher
cam_policy_*.json     — CAM policy files for SCF execution role
```

## How It Works

1. **Resource Discovery** — Calls Tag `GetResources` (single global call) to enumerate all resources (tagged and untagged)
2. **Deduplication** — Removes duplicate entries when the same resource appears under multiple service types (e.g. `ccs` → `tke`, `ci` → `cos`) and filters known ghost prefixes (e.g. `eks-*` under `cvm`)
3. **Enrichment** — For supported services, calls Describe APIs to get resource type, payment model, status, and name
4. **Ghost Filtering** — For validated services, resources not found by their service API are removed as ghost/orphaned entries
5. **Output** — Generates a CSV and writes to `/tmp` (+ optional COS upload)

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

Currently implemented enrichers that fetch resource name, type, payment model, status, and creation date:

| Service | Enricher | APIs Used |
|---|---|---|
| CVM | `enrichers/cvm.py` | `cvm:DescribeInstances` |
| CBS | `enrichers/cbs.py` | `cbs:DescribeDisks` |
| CLB | `enrichers/clb.py` | `clb:DescribeLoadBalancers` |
| MySQL (CDB) | `enrichers/mysql.py` | `cdb:DescribeDBInstances` |
| Redis | `enrichers/redis_enrich.py` | `redis:DescribeInstances` |
| GAAP | `enrichers/gaap.py` | `gaap:DescribeProxies`, `gaap:DescribeProxyGroupList`, `gaap:DescribeRealServers` |
| VPC | `enrichers/vpc.py` | `vpc:DescribeVpcs`, `vpc:DescribeSubnets`, `vpc:DescribeNetworkAcls`, `vpc:DescribeSecurityGroups`, `vpc:DescribeAddresses`, `vpc:DescribeRouteTables` |
| Auto Scaling | `enrichers/autoscaling.py` | `as:DescribeAutoScalingGroups`, `as:DescribeLaunchConfigurations` |
| CAM | `enrichers/cam.py` | `cam:DescribeRoleList`, `cam:GetPolicy` |
| TKE | `enrichers/tke.py` | `tke:DescribeClusters` |
| SSL Certificates | `enrichers/ssl_cert.py` | `ssl:DescribeCertificates` |
| SCF | `enrichers/scf.py` | `scf:ListFunctions` |
| CLS | `enrichers/cls_enrich.py` | `cls:DescribeTopics`, `cls:DescribeLogsets` |
| Lighthouse | `enrichers/lighthouse_enrich.py` | `lighthouse:DescribeInstances`, `lighthouse:DescribeBlueprints` |
| API Gateway | `enrichers/apigw.py` | `apigw:DescribeServicesStatus` |
| COS | `enrichers/cos.py` | `cos:GetService` (ListBuckets) |
| TAT | `enrichers/tat_enrich.py` | `tat:DescribeCommands` |
| Live Streaming | `enrichers/live_enrich.py` | `live:DescribeLiveDomains` |
| Monitor (TCOP) | `enrichers/monitor_enrich.py` | `monitor:DescribeGrafanaInstances`, `monitor:DescribePrometheusInstances`, `monitor:DescribeAlarmNotices` |
| VOD | `enrichers/vod_enrich.py` | `vod:DescribeSubAppIds` |
| Organization | `enrichers/organization_enrich.py` | `organization:DescribeOrganizationNodes`, `organization:DescribeOrganizationMembers` |
| RUM | `enrichers/rum_enrich.py` | `rum:DescribeProjects` |
| CTSDB | `enrichers/ctsdb_enrich.py` | `ctsdb:DescribeClusters` |
| Private DNS | `enrichers/privatedns_enrich.py` | `privatedns:DescribePrivateZoneList` |
| TI-ONE | `enrichers/tione_enrich.py` | *(no API — SDK lacks training task Describe)* |

All other services fall back to `enrichers/generic.py` — resources still appear in the CSV with their tags, but type/payment/status fields will be empty until a specific enricher is added.

**No enrichment API available:** TRTC (no `DescribeApplications` in SDK), GME (no app listing API), TI-ONE (no training task API).

### Ghost Resource Filtering

Services listed in `VALIDATED_SERVICES` (`gaap`, `cvm`, `vpc`, `as`, `clb`, `cbs`, `cdb`, `redis`, `tke`, `ssl`, `privatedns`) have API-validated enrichers. After enrichment, any resource belonging to a validated service that was **not** returned by its Describe API is considered a ghost/orphaned entry (exists in the Tag API but not in the actual service) and is removed from the final output.

## SCF Deployment

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `COS_BUCKET` | **Yes** | COS bucket name (e.g. `inventory-1250000000`) |
| `COS_REGION` | **Yes** | COS bucket region (e.g. `ap-singapore`) |
| `COS_KEY_PREFIX` | No | COS folder prefix (default: `inventory/`) |

> **Credentials:** When an execution role is bound to the SCF function, Tencent Cloud automatically injects `TENCENTCLOUD_SECRETID`, `TENCENTCLOUD_SECRETKEY`, and `TENCENTCLOUD_SESSIONTOKEN` as environment variables. No manual credential configuration is needed.

### SCF Configuration

| Setting | Value |
|---|---|
| Runtime | Python 3.9+ |
| Handler | `index.main_handler` |
| Timeout | 900 seconds (max) |
| Memory | 256 MB (recommended) |
| Trigger | Timer (cron) — e.g. daily |

### First-time Deployment

Upload `deploy/tc-account-inventory.zip` as the SCF function code package.

### Subsequent Updates

Upload changed `.py` files directly via SCF console code editor — **do not rebuild the zip**.

## CAM Policy

The SCF execution role needs **read-only** access across the account plus COS write for uploading the inventory CSV. The role must have **trust entity** `scf.tencentcloudapi.com`.

| Approach | Policy | File |
|---|---|---|
| **Recommended** | `ReadOnlyAccess` managed policy + custom COS write | [`cam_policy_cos_write.json`](cam_policy_cos_write.json) |
| **Least-privilege** | Granular — only the specific APIs used by this tool | [`cam_policy_least_privilege.json`](cam_policy_least_privilege.json) |

> Replace `your-bucket-name` in the COS write policy with your actual bucket name.

## SCF Testing Checklist

### Pre-Deploy
- [ ] Set env vars in SCF console: `COS_BUCKET`, `COS_REGION`
- [ ] CAM execution role attached to SCF (trust entity: `scf.tencentcloudapi.com`) with `ReadOnlyAccess` + COS `PutObject`
- [ ] Timeout set to **900s**, memory **256MB**
- [ ] Handler set to **`index.main_handler`**
- [ ] Runtime: **Python 3.9+**

### Smoke Test (SCF Console → Test)
- [ ] Invoke with empty `{}` event — should return `statusCode: 200`
- [ ] Check logs for `[*] Discovering all resources` — confirms auth works
- [ ] Check logs for `[*] Enriching resources` — confirms Tag API access
- [ ] Verify no `[ERROR]` in output

### Validation
- [ ] Check `total_resources` in response > 0
- [ ] Check `/tmp/inventory.csv` exists (visible in logs)
- [ ] Spot-check a known resource ID appears in output
- [ ] Verify enriched fields (ResourceType, PaymentModel) populated for CVM/CBS/CLB/VPC/GAAP/AS
- [ ] Verify ghost resources filtered out (check `[GHOST]` log line)
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
3. If the enricher validates existence (only returns entries for resources that actually exist), add the service to `VALIDATED_SERVICES` in `inventory.py` to enable ghost filtering
4. Add required API permissions to `cam_policy_least_privilege.json`
5. Upload updated files via SCF code editor

## SDK Reference

- [tencentcloud-sdk-python-intl-en](https://github.com/TencentCloud/tencentcloud-sdk-python-intl-en/tree/master/tencentcloud)
