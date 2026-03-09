"""API Gateway enricher — extract creation dates for APIGW services."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.apigateway.v20180808 import apigateway_client, models


def enrich_apigw(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "apigateway.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = apigateway_client.ApigatewayClient(cred, region, cp)

    result = {}

    try:
        all_services = {}
        offset = 0
        while True:
            req = models.DescribeServicesStatusRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 100}))
            resp = client.DescribeServicesStatus(req)
            for s in (resp.Result.ServiceSet if resp.Result else []) or []:
                all_services[s.ServiceId] = {
                    "ResourceType": s.Protocol or "",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": s.ServiceName or "",
                    "CreationDate": s.CreatedTime or "",
                }
            total = resp.Result.TotalCount if resp.Result else 0
            if not (resp.Result and resp.Result.ServiceSet) or offset + 100 >= total:
                break
            offset += 100

        for rid in resource_ids:
            result[rid] = all_services.get(rid, {
                "ResourceType": "",
                "PaymentModel": "",
                "Status": "",
                "Name": "",
                "CreationDate": "",
            })
    except TencentCloudSDKException as e:
        print(f"  [WARN] APIGW DescribeServicesStatus error: {e}")
        for rid in resource_ids:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
