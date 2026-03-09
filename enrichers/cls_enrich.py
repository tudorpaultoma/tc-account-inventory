"""CLS enricher — extract creation dates for CLS topics and logsets."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cls.v20201016 import cls_client, models


def _make_client(cred, region):
    hp = HttpProfile()
    hp.endpoint = "cls.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    return cls_client.ClsClient(cred, region, cp)


def enrich_cls(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    client = _make_client(cred, region)
    result = {}

    # Separate topics and logsets by UUID format (both are UUIDs but different API)
    # We'll try both APIs and merge results

    # Topics
    try:
        offset = 0
        while True:
            req = models.DescribeTopicsRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 50}))
            resp = client.DescribeTopics(req)
            for t in (resp.Topics or []):
                result[t.TopicId] = {
                    "ResourceType": "topic",
                    "PaymentModel": "",
                    "Status": t.Status if hasattr(t, "Status") else "",
                    "Name": t.TopicName or "",
                    "CreationDate": t.CreateTime or "",
                }
            if not resp.Topics or offset + 50 >= (resp.TotalCount or 0):
                break
            offset += 50
    except TencentCloudSDKException as e:
        print(f"  [WARN] CLS DescribeTopics error: {e}")

    # Logsets
    try:
        offset = 0
        while True:
            req = models.DescribeLogsetsRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 50}))
            resp = client.DescribeLogsets(req)
            for ls in (resp.Logsets or []):
                result[ls.LogsetId] = {
                    "ResourceType": "logset",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": ls.LogsetName or "",
                    "CreationDate": ls.CreateTime or "",
                }
            if not resp.Logsets or offset + 50 >= (resp.TotalCount or 0):
                break
            offset += 50
    except TencentCloudSDKException as e:
        print(f"  [WARN] CLS DescribeLogsets error: {e}")

    # Fill in any IDs not found
    for rid in resource_ids:
        if rid not in result:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
