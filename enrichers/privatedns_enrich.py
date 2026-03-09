"""PrivateDNS enricher — extract creation dates for private DNS zones."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.privatedns.v20201028 import privatedns_client, models


def enrich_privatedns(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "privatedns.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = privatedns_client.PrivatednsClient(cred, "", cp)

    result = {}

    try:
        all_zones = {}
        offset = 0
        while True:
            req = models.DescribePrivateZoneListRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 100}))
            resp = client.DescribePrivateZoneList(req)
            for z in (resp.PrivateZoneSet or []):
                all_zones[z.ZoneId] = {
                    "ResourceType": "zone",
                    "PaymentModel": "",
                    "Status": z.Status or "" if hasattr(z, "Status") else "",
                    "Name": z.Domain or "",
                    "CreationDate": z.CreatedOn or "",
                }
            total = resp.TotalCount or 0
            if not resp.PrivateZoneSet or offset + 100 >= total:
                break
            offset += 100

        found = 0
        for rid in resource_ids:
            if rid in all_zones:
                result[rid] = all_zones[rid]
                found += 1

        ghost = len(resource_ids) - found
        if ghost:
            ghost_ids = [rid for rid in resource_ids if rid not in all_zones]
            print(f"  [PrivateDNS] {found} valid, {ghost} ghost zones: {ghost_ids[:5]}")
    except TencentCloudSDKException as e:
        print(f"  [WARN] PrivateDNS DescribePrivateZoneList error: {e}")
        for rid in resource_ids:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
