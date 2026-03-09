"""Live enricher — extract creation dates for CSS (Live) domains."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.live.v20180801 import live_client, models


def enrich_live(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "live.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = live_client.LiveClient(cred, "", cp)

    result = {}

    try:
        all_domains = {}
        req = models.DescribeLiveDomainsRequest()
        req.from_json_string(json.dumps({}))
        resp = client.DescribeLiveDomains(req)
        for d in (resp.DomainList or []):
            all_domains[d.Name] = {
                "ResourceType": d.Type or "" if hasattr(d, "Type") else "",
                "PaymentModel": "",
                "Status": "",
                "Name": d.Name or "",
                "CreationDate": d.CreateTime or "",
            }

        for rid in resource_ids:
            result[rid] = all_domains.get(rid, {
                "ResourceType": "",
                "PaymentModel": "",
                "Status": "",
                "Name": "",
                "CreationDate": "",
            })
    except TencentCloudSDKException as e:
        print(f"  [WARN] Live DescribeLiveDomains error: {e}")
        for rid in resource_ids:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
