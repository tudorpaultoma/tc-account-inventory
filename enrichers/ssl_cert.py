"""SSL enricher — extract creation dates for SSL certificates."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ssl.v20191205 import ssl_client, models


def enrich_ssl(cred, region, resource_ids):
    """Returns dict: resource_id -> enrichment data with CreationDate."""
    if not resource_ids:
        return {}

    hp = HttpProfile()
    hp.endpoint = "ssl.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    client = ssl_client.SslClient(cred, "", cp)

    result = {}

    # DescribeCertificates returns all certs; filter by ID
    try:
        all_certs = {}
        offset = 0
        while True:
            req = models.DescribeCertificatesRequest()
            req.from_json_string(json.dumps({"Offset": offset, "Limit": 100}))
            resp = client.DescribeCertificates(req)
            for c in (resp.Certificates or []):
                all_certs[c.CertificateId] = {
                    "ResourceType": c.CertificateType or "",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": c.Alias or "",
                    "CreationDate": c.InsertTime or "",
                }
            if not resp.Certificates or len(all_certs) >= (resp.TotalCount or 0):
                break
            offset += 100

        for rid in resource_ids:
            if rid in all_certs:
                result[rid] = all_certs[rid]

        ghost_certs = [rid for rid in resource_ids if rid not in result]
        if ghost_certs:
            print(f"  [SSL] {len(result)} valid, {len(ghost_certs)} ghost certs: {ghost_certs[:5]}{'...' if len(ghost_certs) > 5 else ''}")
    except TencentCloudSDKException as e:
        print(f"  [WARN] SSL DescribeCertificates error: {e}")
        for rid in resource_ids:
            result[rid] = {"ResourceType": "", "PaymentModel": "", "Status": "", "Name": "", "CreationDate": ""}

    return result
