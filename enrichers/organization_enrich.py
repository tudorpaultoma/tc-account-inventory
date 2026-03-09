"""Organization enricher — extract creation dates for org nodes and members."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.organization.v20210331 import organization_client, models


def enrich_organization(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "organization.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = organization_client.OrganizationClient(cred, "", cp)

    result = {}

    # --- Nodes ---
    try:
        offset = 0
        while True:
            req = models.DescribeOrganizationNodesRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 50}))
            resp = client.DescribeOrganizationNodes(req)
            for node in (resp.Items or []):
                key = str(node.NodeId)
                result[key] = {
                    "ResourceType": "node",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": node.Name or "",
                    "CreationDate": node.CreateTime or "",
                }
            total = resp.Total or 0
            if not resp.Items or offset + 50 >= total:
                break
            offset += 50
    except TencentCloudSDKException as e:
        print(f"  [WARN] Organization DescribeOrganizationNodes error: {e}")

    # --- Members ---
    try:
        offset = 0
        while True:
            req = models.DescribeOrganizationMembersRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 50, "Lang": "en"}))
            resp = client.DescribeOrganizationMembers(req)
            for m in (resp.Items or []):
                key = str(m.MemberUin)
                result[key] = {
                    "ResourceType": "member",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": m.Name or "",
                    "CreationDate": m.CreateTime or "",
                }
            total = resp.Total or 0
            if not resp.Items or offset + 50 >= total:
                break
            offset += 50
    except TencentCloudSDKException as e:
        print(f"  [WARN] Organization DescribeOrganizationMembers error: {e}")

    # Fill missing
    for rid in resource_ids:
        if rid not in result:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
