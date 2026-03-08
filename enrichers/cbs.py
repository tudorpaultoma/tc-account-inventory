"""CBS enricher — get disk type, charge type, status."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cbs.v20170312 import cbs_client, models


def enrich_cbs(cred, region, resource_ids):
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "cbs.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = cbs_client.CbsClient(cred, region, cp)

    result = {}
    for i in range(0, len(resource_ids), 100):
        batch = resource_ids[i:i + 100]
        try:
            req = models.DescribeDisksRequest()
            req.from_json_string(json.dumps({
                "DiskIds": batch,
                "Limit": 100,
            }))
            resp = client.DescribeDisks(req)
            if resp.DiskSet:
                for d in resp.DiskSet:
                    result[d.DiskId] = {
                        "ResourceType": d.DiskType or "",
                        "PaymentModel": d.DiskChargeType or "",
                        "Status": d.DiskState or "",
                        "Name": d.DiskName or "",
                    }
        except TencentCloudSDKException as e:
            print(f"  [WARN] CBS enrich error (region={region}): {e}")

    return result
