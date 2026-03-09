"""CAM enricher — extract creation dates for CAM roles and policies."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cam.v20190116 import cam_client, models


def _make_client(cred):
    hp = HttpProfile()
    hp.endpoint = "cam.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    return cam_client.CamClient(cred, "", cp)


def _fetch_roles(client):
    """Fetch all roles. Returns dict: role_id -> info."""
    result = {}
    page = 1
    while True:
        try:
            req = models.DescribeRoleListRequest()
            req.from_json_string(json.dumps({"Page": page, "Rp": 200}))
            resp = client.DescribeRoleList(req)
            for r in (resp.List or []):
                result[str(r.RoleId)] = {
                    "ResourceType": "role",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": r.RoleName or "",
                    "CreationDate": r.AddTime or "",
                }
            if not resp.List or len(resp.List) < 200:
                break
            page += 1
        except TencentCloudSDKException as e:
            print(f"  [WARN] CAM DescribeRoleList error: {e}")
            break
    return result


def _fetch_policies(client, policy_ids):
    """Fetch individual policies by ID. Returns dict: policy_id -> info."""
    result = {}
    for pid in policy_ids:
        try:
            req = models.GetPolicyRequest()
            req.from_json_string(json.dumps({"PolicyId": int(pid)}))
            resp = client.GetPolicy(req)
            result[pid] = {
                "ResourceType": "policy",
                "PaymentModel": "",
                "Status": "",
                "Name": resp.PolicyName or "",
                "CreationDate": resp.AddTime or "",
            }
        except TencentCloudSDKException as e:
            # Policy may not exist or no permission — return without creation date
            result[pid] = {
                "ResourceType": "policy",
                "PaymentModel": "",
                "Status": "",
                "Name": "",
                "CreationDate": "",
            }
    return result


def enrich_cam(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    client = _make_client(cred)
    result = {}

    role_ids = []
    policy_ids = []
    other = []

    for rid in resource_ids:
        # Role IDs are large numeric (e.g. 4611686028425542892)
        # Policy IDs are shorter numeric (e.g. 265680071)
        # We rely on the ARN prefix from the CSV, but here we only get the ID.
        # Heuristic: role IDs are > 10^15, policy IDs are < 10^12
        try:
            val = int(rid)
            if val > 10**15:
                role_ids.append(rid)
            else:
                policy_ids.append(rid)
        except ValueError:
            other.append(rid)

    if role_ids:
        try:
            roles = _fetch_roles(client)
            for rid in role_ids:
                if rid in roles:
                    result[rid] = roles[rid]
                else:
                    result[rid] = {
                        "ResourceType": "role",
                        "PaymentModel": "",
                        "Status": "",
                        "Name": "",
                        "CreationDate": "",
                    }
        except Exception as e:
            print(f"  [WARN] CAM roles error: {e}")
            for rid in role_ids:
                result[rid] = {"ResourceType": "role", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    if policy_ids:
        result.update(_fetch_policies(client, policy_ids))

    for rid in other:
        result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
