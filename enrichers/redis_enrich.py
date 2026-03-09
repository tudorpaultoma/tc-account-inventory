"""Redis enricher — get instance type, billing, status."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.redis.v20180412 import redis_client, models


def enrich_redis(cred, region, resource_ids):
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "redis.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = redis_client.RedisClient(cred, region, cp)

    result = {}
    # Redis DescribeInstances doesn't support filtering by ID list directly;
    # we fetch all and filter locally
    try:
        offset = 0
        all_instances = []
        while True:
            req = models.DescribeInstancesRequest()
            req.from_json_string(json.dumps({
                "Limit": 100,
                "Offset": offset,
            }))
            resp = client.DescribeInstances(req)
            if resp.InstanceSet:
                all_instances.extend(resp.InstanceSet)
            if len(all_instances) >= (resp.TotalCount or 0):
                break
            offset += 100

        id_set = set(resource_ids)
        for inst in all_instances:
            if inst.InstanceId in id_set:
                result[inst.InstanceId] = {
                    "ResourceType": str(inst.Type) if inst.Type is not None else "",
                    "PaymentModel": "PREPAID" if inst.BillingMode == 1 else "POSTPAID",
                    "Status": str(inst.Status) if inst.Status is not None else "",
                    "Name": inst.InstanceName or "",
                    "CreationDate": inst.Createtime or "",
                }
    except TencentCloudSDKException as e:
        print(f"  [WARN] Redis enrich error (region={region}): {e}")

    return result
