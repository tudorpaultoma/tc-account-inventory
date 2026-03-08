"""MySQL (CDB) enricher — get instance type, pay type, status."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cdb.v20170320 import cdb_client, models


def enrich_mysql(cred, region, resource_ids):
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "cdb.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = cdb_client.CdbClient(cred, region, cp)

    result = {}
    for i in range(0, len(resource_ids), 100):
        batch = resource_ids[i:i + 100]
        try:
            req = models.DescribeDBInstancesRequest()
            req.from_json_string(json.dumps({
                "InstanceIds": batch,
                "Limit": 100,
            }))
            resp = client.DescribeDBInstances(req)
            if resp.Items:
                for inst in resp.Items:
                    result[inst.InstanceId] = {
                        "ResourceType": inst.DeviceType or "",
                        "PaymentModel": "PREPAID" if inst.PayType == 0 else "POSTPAID",
                        "Status": str(inst.Status) if inst.Status is not None else "",
                        "Name": inst.InstanceName or "",
                    }
        except TencentCloudSDKException as e:
            print(f"  [WARN] MySQL enrich error (region={region}): {e}")

    return result
