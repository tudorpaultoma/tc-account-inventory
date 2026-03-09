"""Monitor (TCOP) enricher — Grafana instances, Prometheus instances, alarm notices."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.monitor.v20180724 import monitor_client, models


def _make_client(cred, region):
    hp = HttpProfile()
    hp.endpoint = "monitor.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    return monitor_client.MonitorClient(cred, region, cp)


def enrich_monitor(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    # Monitor API requires a real region; "global" is not accepted.
    api_region = "ap-guangzhou" if region in ("global", "") else region
    client = _make_client(cred, api_region)
    result = {}

    grafana_ids = [rid for rid in resource_ids if rid.startswith("grafana-")]
    prom_ids = [rid for rid in resource_ids if rid.startswith("prom-")]
    notice_ids = [rid for rid in resource_ids if rid.startswith("notice-")]
    other = [rid for rid in resource_ids if rid not in grafana_ids + prom_ids + notice_ids]

    # --- Grafana instances ---
    if grafana_ids:
        try:
            req = models.DescribeGrafanaInstancesRequest()
            req.from_json_string(json.dumps({
                "InstanceIds": grafana_ids,
                "Offset": 0,
                "Limit": 100,
            }))
            resp = client.DescribeGrafanaInstances(req)
            for inst in (resp.Instances or resp.InstanceSet or []):
                result[inst.InstanceId] = {
                    "ResourceType": "grafana-instance",
                    "PaymentModel": "",
                    "Status": str(inst.InstanceStatus) if inst.InstanceStatus is not None else "",
                    "Name": inst.InstanceName or "",
                    "CreationDate": inst.CreatedAt or "",
                }
        except TencentCloudSDKException as e:
            print(f"  [WARN] Monitor DescribeGrafanaInstances error: {e}")

    # --- Prometheus instances ---
    if prom_ids:
        try:
            req = models.DescribePrometheusInstancesRequest()
            req.from_json_string(json.dumps({
                "InstanceIds": prom_ids,
                "Limit": 100,
            }))
            resp = client.DescribePrometheusInstances(req)
            for inst in (resp.InstanceSet or []):
                result[inst.InstanceId] = {
                    "ResourceType": "prom-instance",
                    "PaymentModel": "",
                    "Status": str(inst.InstanceStatus) if inst.InstanceStatus is not None else "",
                    "Name": inst.InstanceName or "",
                    "CreationDate": inst.CreatedAt or "",
                }
        except TencentCloudSDKException as e:
            print(f"  [WARN] Monitor DescribePrometheusInstances error: {e}")

    # --- Alarm notices (only UpdatedAt available, no CreatedAt) ---
    if notice_ids:
        try:
            req = models.DescribeAlarmNoticesRequest()
            req.from_json_string(json.dumps({
                "Module": "monitor",
                "NoticeIds": notice_ids,
                "PageNumber": 1,
                "PageSize": 200,
            }))
            resp = client.DescribeAlarmNotices(req)
            for notice in (resp.Notices or []):
                nid = notice.Id or ""
                if nid.startswith("notice-"):
                    result[nid] = {
                        "ResourceType": "cm-notice",
                        "PaymentModel": "",
                        "Status": "",
                        "Name": notice.Name or "",
                        "CreationDate": notice.UpdatedAt or "",  # no CreatedAt available
                    }
        except TencentCloudSDKException as e:
            print(f"  [WARN] Monitor DescribeAlarmNotices error: {e}")

    # Other unknown monitor resource types
    for rid in other:
        if rid not in result:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    # Fill missing
    for rid in resource_ids:
        if rid not in result:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
