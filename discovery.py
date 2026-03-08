"""
Discovery module — uses Tag API (GetResources) to enumerate all resources
across all regions and service types.
"""

import os
import time
import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm.v20170312 import cvm_client, models as cvm_models
from tencentcloud.tag.v20180813 import tag_client, models as tag_models

import config


def get_credentials():
    """Read credentials from env vars at call time (not import time).
    Tries multiple env var names used by different SCF runtimes."""
    secret_id = (
        os.environ.get("TENCENTCLOUD_SECRETID", "")
        or os.environ.get("TENCENTCLOUD_SECRET_ID", "")
        or os.environ.get("SecretId", "")
    )
    secret_key = (
        os.environ.get("TENCENTCLOUD_SECRETKEY", "")
        or os.environ.get("TENCENTCLOUD_SECRET_KEY", "")
        or os.environ.get("SecretKey", "")
    )
    session_token = (
        os.environ.get("TENCENTCLOUD_SESSIONTOKEN", "")
        or os.environ.get("TENCENTCLOUD_SESSION_TOKEN", "")
        or os.environ.get("Token", "")
    )

    if not secret_id or not secret_key:
        raise Exception("Credentials not found in environment.")

    if session_token:
        return credential.Credential(secret_id, secret_key, session_token)
    return credential.Credential(secret_id, secret_key)


def get_regions(cred):
    """Fetch all available regions via CVM DescribeRegions."""
    hp = HttpProfile()
    hp.endpoint = "cvm.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = cvm_client.CvmClient(cred, "", cp)
    req = cvm_models.DescribeRegionsRequest()
    resp = client.DescribeRegions(req)
    return [r.Region for r in resp.RegionSet]


def get_all_resources(cred, region=None):
    """
    Use Tag GetResources to list ALL resources (tagged + untagged).
    If region is None, queries globally.
    Returns list of dicts with keys: Resource, ServiceType, Tags, Region, ResourcePrefix, ResourceId
    """
    hp = HttpProfile()
    hp.endpoint = "tag.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    # Tag API region param is optional; pass empty string for global
    client = tag_client.TagClient(cred, region or "", cp)

    resources = []
    pagination_token = ""

    while True:
        try:
            req = tag_models.GetResourcesRequest()
            params = {"MaxResults": config.TAG_PAGE_SIZE}
            if pagination_token:
                params["PaginationToken"] = pagination_token
            req.from_json_string(json.dumps(params))

            resp = client.GetResources(req)

            if resp.ResourceTagMappingList:
                for item in resp.ResourceTagMappingList:
                    parsed = parse_six_segment(item.Resource)
                    tags = {}
                    if item.Tags:
                        for t in item.Tags:
                            tags[t.TagKey] = t.TagValue
                    resources.append({
                        "ResourceArn": item.Resource,
                        "ServiceType": parsed.get("service_type", ""),
                        "Region": parsed.get("region", region or ""),
                        "ResourcePrefix": parsed.get("resource_prefix", ""),
                        "ResourceId": parsed.get("resource_id", ""),
                        "Tags": tags,
                    })

            pagination_token = resp.PaginationToken if resp.PaginationToken else ""
            if not pagination_token:
                break

            time.sleep(config.API_SLEEP)

        except TencentCloudSDKException as e:
            print(f"  [WARN] Tag GetResources error (region={region}): {e}")
            break

    return resources


def parse_six_segment(arn):
    """
    Parse Tencent Cloud six-segment resource description.
    Format: qcs::ServiceType:Region:Account:ResourcePrefix/ResourceId
    """
    result = {
        "service_type": "",
        "region": "",
        "account": "",
        "resource_prefix": "",
        "resource_id": "",
    }
    if not arn:
        return result

    parts = arn.split(":")
    if len(parts) >= 6:
        result["service_type"] = parts[2]
        result["region"] = parts[3]
        result["account"] = parts[4]
        # Last segment: resourcePrefix/resourceId
        resource_part = ":".join(parts[5:])
        if "/" in resource_part:
            prefix, rid = resource_part.split("/", 1)
            result["resource_prefix"] = prefix
            result["resource_id"] = rid
        else:
            result["resource_prefix"] = resource_part

    return result
