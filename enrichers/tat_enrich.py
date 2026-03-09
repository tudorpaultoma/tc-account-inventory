"""TAT enricher — extract creation dates for TAT commands."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tat.v20201028 import tat_client, models


def enrich_tat(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "tat.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = tat_client.TatClient(cred, region, cp)

    result = {}

    for i in range(0, len(resource_ids), 100):
        batch = resource_ids[i:i + 100]
        try:
            req = models.DescribeCommandsRequest()
            req.from_json_string(json.dumps({"CommandIds": batch, "Limit": 100}))
            resp = client.DescribeCommands(req)
            for c in (resp.CommandSet or []):
                result[c.CommandId] = {
                    "ResourceType": c.CommandType or "",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": c.CommandName or "",
                    "CreationDate": c.CreatedTime or "",
                }
        except TencentCloudSDKException as e:
            print(f"  [WARN] TAT DescribeCommands error: {e}")

    for rid in resource_ids:
        if rid not in result:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
