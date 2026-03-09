"""SCF enricher — extract creation dates for SCF functions."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf.v20180416 import scf_client, models


def enrich_scf(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "scf.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = scf_client.ScfClient(cred, region, cp)

    result = {}

    # SCF resource IDs look like: default/function/my-func-name
    # We need to extract namespace and function name
    try:
        all_funcs = {}
        offset = 0
        while True:
            req = models.ListFunctionsRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 100}))
            resp = client.ListFunctions(req)
            for f in (resp.Functions or []):
                ns = f.Namespace or "default"
                key = f"{ns}/function/{f.FunctionName}"
                all_funcs[key] = {
                    "ResourceType": f.Runtime or "",
                    "PaymentModel": "",
                    "Status": f.Status or "",
                    "Name": f.FunctionName or "",
                    "CreationDate": f.AddTime or "",
                }
            if not resp.Functions or offset + 100 >= (resp.TotalCount or 0):
                break
            offset += 100

        for rid in resource_ids:
            result[rid] = all_funcs.get(rid, {
                "ResourceType": "",
                "PaymentModel": "",
                "Status": "",
                "Name": "",
                "CreationDate": "",
            })
    except TencentCloudSDKException as e:
        print(f"  [WARN] SCF ListFunctions error: {e}")
        for rid in resource_ids:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
