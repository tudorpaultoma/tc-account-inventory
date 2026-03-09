"""CLB enricher — get LB type, charge type, status."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.clb.v20180317 import clb_client, models


def enrich_clb(cred, region, resource_ids):
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "clb.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = clb_client.ClbClient(cred, region, cp)

    result = {}
    # CLB API limit: max 20 IDs per request
    for i in range(0, len(resource_ids), 20):
        batch = resource_ids[i:i + 20]
        try:
            req = models.DescribeLoadBalancersRequest()
            req.from_json_string(json.dumps({
                "LoadBalancerIds": batch,
                "Limit": 100,
            }))
            resp = client.DescribeLoadBalancers(req)
            if resp.LoadBalancerSet:
                for lb in resp.LoadBalancerSet:
                    result[lb.LoadBalancerId] = {
                        "ResourceType": lb.LoadBalancerType or "",
                        "PaymentModel": lb.ChargeType if hasattr(lb, "ChargeType") else "",
                        "Status": str(lb.Status) if lb.Status is not None else "",
                        "Name": lb.LoadBalancerName or "",
                        "CreationDate": lb.CreateTime or "",
                    }
        except TencentCloudSDKException as e:
            print(f"  [WARN] CLB enrich error (region={region}): {e}")

    return result
