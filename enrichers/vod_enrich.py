"""VOD enricher — extract creation dates for VOD sub-applications."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.vod.v20180717 import vod_client, models


def enrich_vod(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "vod.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = vod_client.VodClient(cred, "", cp)

    result = {}

    try:
        all_apps = {}
        offset = 0
        while True:
            req = models.DescribeSubAppIdsRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 200}))
            resp = client.DescribeSubAppIds(req)
            for app in (resp.SubAppIdInfoSet or []):
                key = str(app.SubAppId)
                all_apps[key] = {
                    "ResourceType": "subAppId",
                    "PaymentModel": "",
                    "Status": app.Status or "",
                    "Name": app.SubAppIdName or app.Name or "",
                    "CreationDate": app.CreateTime or "",
                }
            total = resp.TotalCount or 0
            if not resp.SubAppIdInfoSet or offset + 200 >= total:
                break
            offset += 200

        for rid in resource_ids:
            result[rid] = all_apps.get(rid, {
                "ResourceType": "",
                "PaymentModel": "",
                "Status": "",
                "Name": "",
                "CreationDate": "",
            })
    except TencentCloudSDKException as e:
        print(f"  [WARN] VOD DescribeSubAppIds error: {e}")
        for rid in resource_ids:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
