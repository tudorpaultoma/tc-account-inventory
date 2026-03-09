"""CLS enricher — extract creation dates for CLS topics, logsets, alarms, and alarm notices."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cls.v20201016 import cls_client, models


def _make_client(cred, region):
    hp = HttpProfile()
    hp.endpoint = "cls.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    return cls_client.ClsClient(cred, region, cp)


def enrich_cls(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    client = _make_client(cred, region)
    result = {}

    # Separate IDs by type (alarm-*, notice-*, rest are topics/logsets UUIDs)
    alarm_ids = [rid for rid in resource_ids if rid.startswith("alarm-")]
    notice_ids = [rid for rid in resource_ids if rid.startswith("notice-")]
    topic_logset_mg_ids = [rid for rid in resource_ids if rid not in alarm_ids and rid not in notice_ids]

    # Topics
    if topic_logset_mg_ids:
        try:
            offset = 0
            while True:
                req = models.DescribeTopicsRequest()
                req.from_json_string(json.dumps({"Offset": offset, "Limit": 50}))
                resp = client.DescribeTopics(req)
                for t in (resp.Topics or []):
                    result[t.TopicId] = {
                        "ResourceType": "topic",
                        "PaymentModel": "",
                        "Status": t.Status if hasattr(t, "Status") else "",
                        "Name": t.TopicName or "",
                        "CreationDate": t.CreateTime or "",
                    }
                if not resp.Topics or offset + 50 >= (resp.TotalCount or 0):
                    break
                offset += 50
        except TencentCloudSDKException as e:
            print(f"  [WARN] CLS DescribeTopics error: {e}")

    # Logsets
    if topic_logset_mg_ids:
        try:
            offset = 0
            while True:
                req = models.DescribeLogsetsRequest()
                req.from_json_string(json.dumps({"Offset": offset, "Limit": 50}))
                resp = client.DescribeLogsets(req)
                for ls in (resp.Logsets or []):
                    result[ls.LogsetId] = {
                        "ResourceType": "logset",
                        "PaymentModel": "",
                        "Status": "",
                        "Name": ls.LogsetName or "",
                        "CreationDate": ls.CreateTime or "",
                    }
                if not resp.Logsets or offset + 50 >= (resp.TotalCount or 0):
                    break
                offset += 50
        except TencentCloudSDKException as e:
            print(f"  [WARN] CLS DescribeLogsets error: {e}")

    # Machine Groups
    if topic_logset_mg_ids:
        try:
            offset = 0
            while True:
                req = models.DescribeMachineGroupsRequest()
                req.from_json_string(json.dumps({"Offset": offset, "Limit": 100}))
                resp = client.DescribeMachineGroups(req)
                for mg in (resp.MachineGroups or []):
                    result[mg.GroupId] = {
                        "ResourceType": "machineGroup",
                        "PaymentModel": "",
                        "Status": "",
                        "Name": mg.GroupName or "",
                        "CreationDate": mg.CreateTime or "",
                    }
                if not resp.MachineGroups or offset + 100 >= (resp.TotalCount or 0):
                    break
                offset += 100
        except TencentCloudSDKException as e:
            print(f"  [WARN] CLS DescribeMachineGroups error: {e}")

    # Alarms
    if alarm_ids:
        try:
            offset = 0
            while True:
                req = models.DescribeAlarmsRequest()
                req.from_json_string(json.dumps({"Offset": offset, "Limit": 100}))
                resp = client.DescribeAlarms(req)
                for a in (resp.Alarms or []):
                    result[a.AlarmId] = {
                        "ResourceType": "alarm",
                        "PaymentModel": "",
                        "Status": "enabled" if a.Status else "disabled",
                        "Name": a.Name or "",
                        "CreationDate": a.CreateTime or "",
                    }
                if not resp.Alarms or offset + 100 >= (resp.TotalCount or 0):
                    break
                offset += 100
        except TencentCloudSDKException as e:
            print(f"  [WARN] CLS DescribeAlarms error: {e}")

    # Alarm Notices
    if notice_ids:
        try:
            offset = 0
            while True:
                req = models.DescribeAlarmNoticesRequest()
                req.from_json_string(json.dumps({"Offset": offset, "Limit": 100}))
                resp = client.DescribeAlarmNotices(req)
                for n in (resp.AlarmNotices or []):
                    result[n.AlarmNoticeId] = {
                        "ResourceType": "alarm-notice",
                        "PaymentModel": "",
                        "Status": "",
                        "Name": n.Name or "",
                        "CreationDate": n.CreateTime or "",
                    }
                if not resp.AlarmNotices or offset + 100 >= (resp.TotalCount or 0):
                    break
                offset += 100
        except TencentCloudSDKException as e:
            print(f"  [WARN] CLS DescribeAlarmNotices error: {e}")

    # Fill in any IDs not found
    for rid in resource_ids:
        if rid not in result:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
