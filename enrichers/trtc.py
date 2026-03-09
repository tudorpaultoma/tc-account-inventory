"""TRTC enricher — verify SdkAppId existence via DescribeRoomInfo.

Attempts to query room info for each SdkAppId. Invalid apps return specific error codes.
"""

import json
from datetime import datetime, timedelta, timezone
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.trtc.v20190722 import trtc_client, models


def enrich_trtc(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data. Only verified apps are returned."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "trtc.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = trtc_client.TrtcClient(cred, "ap-guangzhou", cp)

    result = {}

    # Use DescribeRoomInfo to validate each SdkAppId
    # Valid apps will succeed or return empty room list
    # Invalid apps will return InvalidParameter or similar errors
    now = datetime.now(timezone.utc)
    start_time = int((now - timedelta(days=1)).timestamp())
    end_time = int(now.timestamp())

    for rid in resource_ids:
        try:
            req = models.DescribeRoomInfoRequest()
            req.from_json_string(json.dumps({
                "SdkAppId": str(rid),
                "StartTime": start_time,
                "EndTime": end_time,
                "PageNumber": "1",
                "PageSize": "1",
            }))
            client.DescribeRoomInfo(req)
            # Success = app exists (even if no rooms)
            result[rid] = {
                "ResourceType": "app",
                "PaymentModel": "",
                "Status": "",
                "Name": "",
                "CreationDate": "",
            }
        except TencentCloudSDKException as e:
            error_code = str(e.code) if hasattr(e, 'code') else str(e)
            # Ghost indicators: InvalidParameter, ResourceNotFound, InvalidSdkAppId
            if any(code in error_code for code in ["InvalidParameter", "ResourceNotFound", "InvalidSdkAppId"]):
                # Ghost app - don't add to result
                pass
            else:
                # Other errors - assume valid to avoid false ghosts
                print(f"  [TRTC] Non-ghost error for {rid}: {error_code}")
                result[rid] = {
                    "ResourceType": "app",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": "",
                    "CreationDate": "",
                }

    found = len(result)
    ghost = len(resource_ids) - found
    if ghost:
        ghost_ids = [rid for rid in resource_ids if rid not in result]
        print(f"  [TRTC] {found} valid, {ghost} ghost resources: {ghost_ids[:5]}")

    return result
