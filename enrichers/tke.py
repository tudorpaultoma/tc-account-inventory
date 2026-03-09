"""TKE enricher — extract creation dates for TKE clusters."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tke.v20180525 import tke_client, models


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
    other = [rid for rid in resource_ids if rid not in cluster_ids]

    # Clusters
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

    # Non-cluster resources (machines, nodepool refs) — keep with empty dates
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
