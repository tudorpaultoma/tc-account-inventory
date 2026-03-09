"""GME enricher — extract creation dates using DescribeApplicationList (raw API call).

The intl SDK lacks this method, so we use CommonClient.call_json to call it directly.
"""

from datetime import datetime, timezone
from tencentcloud.common.common_client import CommonClient
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException


def enrich_gme(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "gme.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = CommonClient("gme", "2018-07-11", cred, "", profile=cp)

    result = {}

    try:
        # GME API requires ProjectId, PageNo, PageSize, SearchText parameters
        # ProjectId: 0=default project, -1=all projects
        resp = client.call_json("DescribeApplicationList", {
            "ProjectId": -1,  # Query all projects
            "PageNo": 0,      # First page
            "PageSize": 200,  # Max 200 per page (default)
            "SearchText": "", # Empty = all apps
        })
        app_list = resp.get("Response", {}).get("ApplicationList", []) or []

        app_map = {}
        for app in app_list:
            biz_id = str(app.get("BizId", ""))
            create_time_unix = app.get("CreateTime", 0)
            # Convert Unix timestamp to ISO 8601 format
            create_date = ""
            if create_time_unix:
                try:
                    dt = datetime.fromtimestamp(int(create_time_unix), tz=timezone.utc)
                    create_date = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except:
                    pass
            
            app_map[biz_id] = {
                "ResourceType": "app",
                "PaymentModel": "",
                "Status": "",
                "Name": app.get("AppName", ""),
                "CreationDate": create_date,
            }

        for rid in resource_ids:
            if rid in app_map:
                result[rid] = app_map[rid]

        found = len(result)
        ghost = len(resource_ids) - found
        if ghost:
            ghost_ids = [rid for rid in resource_ids if rid not in result]
            print(f"  [GME] {found} valid, {ghost} ghost resources: {ghost_ids[:5]}")

    except TencentCloudSDKException as e:
        print(f"  [WARN] GME DescribeApplicationList error: {e}")

    return result
