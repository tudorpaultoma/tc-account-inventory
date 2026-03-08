"""CVM enricher — get instance type, charge type, status."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm.v20170312 import cvm_client, models


def enrich_cvm(cred, region, resource_ids):
    """
    Returns dict: resource_id -> {ResourceType, PaymentModel, Status, Name}
    Only enriches actual CVM instances (ins-* IDs).
    """
    # Filter to only CVM instance IDs — Tag API also returns snapshots, images,
    # security groups, EKS nodes, EIPs, launch templates under "cvm" service type
    cvm_ids = [rid for rid in resource_ids if rid.startswith("ins-")]
    if not cvm_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "cvm.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = cvm_client.CvmClient(cred, region, cp)

    result = {}
    # Batch in groups of 100
    for i in range(0, len(cvm_ids), 100):
        batch = cvm_ids[i:i + 100]
        try:
            req = models.DescribeInstancesRequest()
            req.from_json_string(json.dumps({
                "InstanceIds": batch,
                "Limit": 100,
            }))
            resp = client.DescribeInstances(req)
            if resp.InstanceSet:
                for inst in resp.InstanceSet:
                    result[inst.InstanceId] = {
                        "ResourceType": inst.InstanceType or "",
                        "PaymentModel": inst.InstanceChargeType or "",
                        "Status": inst.InstanceState or "",
                        "Name": inst.InstanceName or "",
                    }
        except TencentCloudSDKException as e:
            print(f"  [WARN] CVM enrich error (region={region}): {e}")

    return result
