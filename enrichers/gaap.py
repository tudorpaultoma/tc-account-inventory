"""GAAP enricher — validate and enrich Global Application Acceleration resources."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.gaap.v20180529 import gaap_client, models


def _make_client(cred):
    hp = HttpProfile()
    hp.endpoint = "gaap.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    return gaap_client.GaapClient(cred, "", cp)


def _fetch_proxies(client):
    """Fetch all proxies (link-*). Returns dict: proxy_id -> info."""
    result = {}
    offset = 0
    while True:
        req = models.DescribeProxiesRequest()
        req.from_json_string(json.dumps({"Offset": offset, "Limit": 100}))
        resp = client.DescribeProxies(req)
        for p in (resp.ProxySet or []):
            result[p.InstanceId] = {
                "ResourceType": "proxy",
                "PaymentModel": "",
                "Status": p.Status or "",
                "Name": p.ProxyName or "",
            }
        if not resp.ProxySet or len(result) >= (resp.TotalCount or 0):
            break
        offset += 100
    return result


def _fetch_proxy_groups(client):
    """Fetch all proxy groups (lg-*). Returns dict: group_id -> info."""
    result = {}
    offset = 0
    while True:
        req = models.DescribeProxyGroupListRequest()
        req.from_json_string(json.dumps({
            "Offset": offset, "Limit": 100, "ProjectId": -1,
        }))
        resp = client.DescribeProxyGroupList(req)
        for g in (resp.ProxyGroupList or []):
            result[g.GroupId] = {
                "ResourceType": "proxyGroup",
                "PaymentModel": "",
                "Status": g.Status or "",
                "Name": g.GroupName or "",
            }
        if not resp.ProxyGroupList or len(result) >= (resp.TotalCount or 0):
            break
        offset += 100
    return result


def _fetch_real_servers(client):
    """Fetch all real servers (rs-*). Returns dict: rs_id -> info."""
    result = {}
    offset = 0
    while True:
        req = models.DescribeRealServersRequest()
        req.from_json_string(json.dumps({
            "Offset": offset, "Limit": 50, "ProjectId": -1,
        }))
        resp = client.DescribeRealServers(req)
        for rs in (resp.RealServerSet or []):
            result[rs.RealServerId] = {
                "ResourceType": "realServer",
                "PaymentModel": "",
                "Status": "",
                "Name": rs.RealServerName or "",
            }
        if not resp.RealServerSet or len(result) >= (resp.TotalCount or 0):
            break
        offset += 50
    return result


def enrich_gaap(cred, region, resource_ids):
    """
    Returns dict: resource_id -> {ResourceType, PaymentModel, Status, Name}
    Only returns entries for resources that actually exist in the GAAP API.
    Missing IDs (ghosts) are omitted — caller can use this to filter them out.
    """
    if not resource_ids:
        return {}

    client = _make_client(cred)
    valid = {}

    try:
        proxies = _fetch_proxies(client)
        valid.update(proxies)
    except TencentCloudSDKException as e:
        print(f"  [WARN] GAAP DescribeProxies error: {e}")

    try:
        groups = _fetch_proxy_groups(client)
        valid.update(groups)
    except TencentCloudSDKException as e:
        print(f"  [WARN] GAAP DescribeProxyGroupList error: {e}")

    try:
        servers = _fetch_real_servers(client)
        valid.update(servers)
    except TencentCloudSDKException as e:
        print(f"  [WARN] GAAP DescribeRealServers error: {e}")

    # Only return enrichment for IDs that were requested AND found
    result = {}
    for rid in resource_ids:
        if rid in valid:
            result[rid] = valid[rid]
        # domain IDs (dm-*) can't be directly listed — keep them if a proxy exists
        elif rid.startswith("dm-"):
            result[rid] = {
                "ResourceType": "domain",
                "PaymentModel": "",
                "Status": "",
                "Name": "",
            }

    found = len(result)
    ghost = len(resource_ids) - found
    if ghost:
        ghost_ids = [rid for rid in resource_ids if rid not in result]
        print(f"  [GAAP] {found} valid, {ghost} ghost resources: {ghost_ids[:5]}{'...' if ghost > 5 else ''}")

    return result
