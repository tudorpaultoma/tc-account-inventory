"""Lighthouse enricher — extract creation dates for Lighthouse instances."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.lighthouse.v20200324 import lighthouse_client, models


def enrich_lighthouse(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "lighthouse.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = lighthouse_client.LighthouseClient(cred, region, cp)

    result = {}
    instance_ids = [rid for rid in resource_ids if rid.startswith("lhins-")]
    other = [rid for rid in resource_ids if not rid.startswith("lhins-")]

    # Instances
    for i in range(0, len(instance_ids), 100):
        batch = instance_ids[i:i + 100]
        try:
            req = models.DescribeInstancesRequest()
            req.from_json_string(json.dumps({"InstanceIds": batch, "Limit": 100}))
            resp = client.DescribeInstances(req)
            for inst in (resp.InstanceSet or []):
                result[inst.InstanceId] = {
                    "ResourceType": inst.BundleId or "",
                    "PaymentModel": "",
                    "Status": inst.InstanceState or "",
                    "Name": inst.InstanceName or "",
                    "CreationDate": inst.CreatedTime or "",
                }
        except TencentCloudSDKException as e:
            print(f"  [WARN] Lighthouse DescribeInstances error: {e}")

    # Blueprints
    blueprint_ids = [rid for rid in other if rid.startswith("lhbp-")]
    remaining = [rid for rid in other if not rid.startswith("lhbp-")]

    for i in range(0, len(blueprint_ids), 100):
        batch = blueprint_ids[i:i + 100]
        try:
            req = models.DescribeBlueprintsRequest()
            req.from_json_string(json.dumps({"BlueprintIds": batch, "Limit": 100}))
            resp = client.DescribeBlueprints(req)
            for bp in (resp.BlueprintSet or []):
                result[bp.BlueprintId] = {
                    "ResourceType": bp.BlueprintType or "",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": bp.DisplayTitle or "" if hasattr(bp, "DisplayTitle") else "",
                    "CreationDate": bp.CreatedTime or "",
                }
        except TencentCloudSDKException as e:
            print(f"  [WARN] Lighthouse DescribeBlueprints error: {e}")

    # Other unknown resource types — keep with empty dates
    for rid in remaining:
        result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    # Instance/blueprint IDs not found — still keep
    for rid in instance_ids + blueprint_ids:
        if rid not in result:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
