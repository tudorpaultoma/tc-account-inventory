"""Auto Scaling enricher — validate and enrich AS resources."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.autoscaling.v20180419 import autoscaling_client, models


def enrich_autoscaling(cred, region, resource_ids):
    """
    Returns dict: resource_id -> {ResourceType, PaymentModel, Status, Name}
    Only returns entries for resources that actually exist.
    """
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "as.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = autoscaling_client.AutoscalingClient(cred, region, cp)

    result = {}
    asg_ids = [rid for rid in resource_ids if rid.startswith("asg-")]
    asc_ids = [rid for rid in resource_ids if rid.startswith("asc-")]
    other = [rid for rid in resource_ids if not rid.startswith("asg-") and not rid.startswith("asc-")]

    # Auto Scaling Groups
    for i in range(0, len(asg_ids), 100):
        batch = asg_ids[i:i + 100]
        try:
            req = models.DescribeAutoScalingGroupsRequest()
            req.from_json_string(json.dumps({
                "AutoScalingGroupIds": batch,
                "Limit": 100,
            }))
            resp = client.DescribeAutoScalingGroups(req)
            for g in (resp.AutoScalingGroupSet or []):
                result[g.AutoScalingGroupId] = {
                    "ResourceType": "",
                    "PaymentModel": "",
                    "Status": g.AutoScalingGroupStatus or "",
                    "Name": g.AutoScalingGroupName or "",
                    "CreationDate": g.CreatedTime or "",
                }
        except TencentCloudSDKException as e:
            print(f"  [WARN] AS DescribeAutoScalingGroups error: {e}")

    # Launch Configurations
    for i in range(0, len(asc_ids), 100):
        batch = asc_ids[i:i + 100]
        try:
            req = models.DescribeLaunchConfigurationsRequest()
            req.from_json_string(json.dumps({
                "LaunchConfigurationIds": batch,
                "Limit": 100,
            }))
            resp = client.DescribeLaunchConfigurations(req)
            for lc in (resp.LaunchConfigurationSet or []):
                result[lc.LaunchConfigurationId] = {
                    "ResourceType": "",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": lc.LaunchConfigurationName or "",
                    "CreationDate": lc.CreatedTime or "",
                }
        except TencentCloudSDKException as e:
            print(f"  [WARN] AS DescribeLaunchConfigurations error: {e}")

    # Keep unknown-prefix resources (don't flag as ghost)
    for rid in other:
        result[rid] = {
            "ResourceType": "",
            "PaymentModel": "",
            "Status": "",
            "Name": "",
            "CreationDate": "",
        }

    # Keep unknown-prefix resources only — don't re-add missing asg-/asc- IDs
    # since AS is in VALIDATED_SERVICES and ghost filter will remove them

    found = len(result)
    ghost = len(resource_ids) - len(other) - found
    if ghost:
        ghost_ids = [rid for rid in asg_ids + asc_ids if rid not in result]
        print(f"  [AS] {found} valid, {ghost} ghost resources: {ghost_ids[:5]}{'...' if ghost > 5 else ''}")

    return result
