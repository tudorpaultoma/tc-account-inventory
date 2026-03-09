"""TKE enricher — extract creation dates for TKE clusters and machines."""

import json
from collections import defaultdict
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tke.v20180525 import tke_client, models


def _fetch_cluster_instances(client, cluster_id):
    """Paginate DescribeClusterInstances and return dict: InstanceId -> instance."""
    instances = {}
    offset = 0
    while True:
        req = models.DescribeClusterInstancesRequest()
        req.from_json_string(json.dumps({
            "ClusterId": cluster_id,
            "Offset": offset,
            "Limit": 100,
        }))
        resp = client.DescribeClusterInstances(req)
        for inst in (resp.InstanceSet or []):
            instances[inst.InstanceId] = inst
        total = resp.TotalCount or 0
        if not resp.InstanceSet or offset + 100 >= total:
            break
        offset += 100
    return instances


def enrich_tke(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "tke.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = tke_client.TkeClient(cred, region, cp)

    result = {}
    cluster_ids = [rid for rid in resource_ids if rid.startswith("cls-") and "_" not in rid]
    # Machine resources: cls-xxx_np-yyy or cls-xxx_ins-yyy
    machine_ids = [rid for rid in resource_ids if "_" in rid and rid.startswith("cls-")]
    other = [rid for rid in resource_ids if rid not in cluster_ids and rid not in machine_ids]

    # ── Clusters ──
    for i in range(0, len(cluster_ids), 100):
        batch = cluster_ids[i:i + 100]
        try:
            req = models.DescribeClustersRequest()
            req.from_json_string(json.dumps({"ClusterIds": batch, "Limit": 100}))
            resp = client.DescribeClusters(req)
            for c in (resp.Clusters or []):
                result[c.ClusterId] = {
                    "ResourceType": c.ClusterType or "",
                    "PaymentModel": "",
                    "Status": c.ClusterStatus or "",
                    "Name": c.ClusterName or "",
                    "CreationDate": c.CreatedTime or "",
                }
        except TencentCloudSDKException as e:
            print(f"  [WARN] TKE DescribeClusters error: {e}")

    # ── Machines / node-pool refs (format: cls-xxx_np-yyy-zzz) ──
    if machine_ids:
        # Group by parent cluster
        cluster_machines = defaultdict(list)
        for rid in machine_ids:
            parent_cluster = rid.split("_", 1)[0]
            cluster_machines[parent_cluster].append(rid)

        for parent_cluster, rids in cluster_machines.items():
            try:
                instances = _fetch_cluster_instances(client, parent_cluster)
                # Build lookup: InstanceId -> instance (API returns InstanceId
                # as either ins-xxx for CVM nodes or np-poolId-suffix for super nodes)
                inst_by_id = {inst.InstanceId: inst for inst in instances.values()}

                for rid in rids:
                    # Extract the machine suffix after cls-xxx_
                    machine_suffix = rid.split("_", 1)[1]
                    matched = inst_by_id.get(machine_suffix)
                    if matched:
                        result[rid] = {
                            "ResourceType": "machine",
                            "PaymentModel": "",
                            "Status": getattr(matched, "InstanceState", "") or "",
                            "Name": "",
                            "CreationDate": getattr(matched, "CreatedTime", "") or "",
                        }
                    else:
                        # Fallback: still record it but without creation date
                        result[rid] = {
                            "ResourceType": "machine",
                            "PaymentModel": "",
                            "Status": "",
                            "Name": "",
                            "CreationDate": "",
                        }
            except TencentCloudSDKException as e:
                print(f"  [WARN] TKE DescribeClusterInstances({parent_cluster}) error: {e}")
                for rid in rids:
                    result[rid] = {
                        "ResourceType": "machine",
                        "PaymentModel": "",
                        "Status": "",
                        "Name": "",
                        "CreationDate": "",
                    }

    # Remaining non-cluster, non-machine resources
    for rid in other:
        result[rid] = {
            "ResourceType": "",
            "PaymentModel": "",
            "Status": "",
            "Name": "",
            "CreationDate": "",
        }

    # Log ghost clusters
    ghost_clusters = [rid for rid in cluster_ids if rid not in result]
    if ghost_clusters:
        print(f"  [TKE] {len(cluster_ids) - len(ghost_clusters)} valid, {len(ghost_clusters)} ghost clusters: {ghost_clusters[:5]}{'...' if len(ghost_clusters) > 5 else ''}")

    return result
