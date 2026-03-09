"""RUM enricher — extract creation dates for RUM instances/projects."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.rum.v20210622 import rum_client, models


def enrich_rum(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "rum.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = rum_client.RumClient(cred, "", cp)

    result = {}

    try:
        all_projects = {}
        offset = 0
        while True:
            req = models.DescribeProjectsRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 100}))
            resp = client.DescribeProjects(req)
            for p in (resp.ProjectSet or []):
                # Tag API uses InstanceID as resource ID (e.g. rum-6qIK83UBXPWXjk)
                if p.InstanceID:
                    all_projects[p.InstanceID] = {
                        "ResourceType": "Instance",
                        "PaymentModel": "",
                        "Status": "",
                        "Name": p.Name or "",
                        "CreationDate": p.CreateTime or "",
                    }
            total = resp.TotalCount or 0
            if not resp.ProjectSet or offset + 100 >= total:
                break
            offset += 100

        for rid in resource_ids:
            result[rid] = all_projects.get(rid, {
                "ResourceType": "",
                "PaymentModel": "",
                "Status": "",
                "Name": "",
                "CreationDate": "",
            })
    except TencentCloudSDKException as e:
        print(f"  [WARN] RUM DescribeProjects error: {e}")
        for rid in resource_ids:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
