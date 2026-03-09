"""VPC enricher — validate and enrich VPC resources (vpcs, subnets, ACLs, SGs, EIPs, route tables)."""

import json
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.vpc.v20170312 import vpc_client, models


def _make_client(cred, region):
    hp = HttpProfile()
    hp.endpoint = "vpc.intl.tencentcloudapi.com"
    cp = ClientProfile()
    cp.httpProfile = hp
    return vpc_client.VpcClient(cred, region, cp)


def _fetch_by_ids(client, id_list, api_method, req_class, id_param, resp_attr, id_field, name_field):
    """Generic paginated fetch-by-IDs for VPC sub-resources."""
    result = {}
    for i in range(0, len(id_list), 100):
        batch = id_list[i:i + 100]
        try:
            req = req_class()
            req.from_json_string(json.dumps({id_param: batch}))
            resp = getattr(client, api_method)(req)
            items = getattr(resp, resp_attr, None) or []
            for item in items:
                rid = getattr(item, id_field)
                name = getattr(item, name_field, "") or ""
                created = getattr(item, "CreatedTime", "") or ""
                result[rid] = {
                    "ResourceType": "",
                    "PaymentModel": "",
                    "Status": "",
                    "Name": name,
                    "CreationDate": created,
                }
        except TencentCloudSDKException as e:
            print(f"  [WARN] VPC {api_method} error: {e}")
    return result


def enrich_vpc(cred, region, resource_ids):
    """
    Returns dict: resource_id -> {ResourceType, PaymentModel, Status, Name}
    Only returns entries for resources that actually exist.
    """
    if not resource_ids:
        return {}

    # Address templates are global resources but VPC API requires a real region
    effective_region = region if region and region != "global" else "ap-singapore"
    client = _make_client(cred, effective_region)
    result = {}

    # Group IDs by prefix
    groups = {
        "vpc-": [], "subnet-": [], "acl-": [], "sg-": [],
        "eip-": [], "eipv6-": [], "rtb-": [], "ipm-": [], "ipmg-": [],
    }
    other = []
    for rid in resource_ids:
        matched = False
        # Check longer prefixes first to avoid ipmg- matching ipm-
        for prefix in sorted(groups.keys(), key=len, reverse=True):
            if rid.startswith(prefix):
                groups[prefix].append(rid)
                matched = True
                break
        if not matched:
            other.append(rid)

    # VPCs
    if groups["vpc-"]:
        result.update(_fetch_by_ids(
            client, groups["vpc-"],
            "DescribeVpcs", models.DescribeVpcsRequest,
            "VpcIds", "VpcSet", "VpcId", "VpcName",
        ))

    # Subnets
    if groups["subnet-"]:
        result.update(_fetch_by_ids(
            client, groups["subnet-"],
            "DescribeSubnets", models.DescribeSubnetsRequest,
            "SubnetIds", "SubnetSet", "SubnetId", "SubnetName",
        ))

    # Network ACLs
    if groups["acl-"]:
        result.update(_fetch_by_ids(
            client, groups["acl-"],
            "DescribeNetworkAcls", models.DescribeNetworkAclsRequest,
            "NetworkAclIds", "NetworkAclSet", "NetworkAclId", "NetworkAclName",
        ))

    # Security Groups
    if groups["sg-"]:
        result.update(_fetch_by_ids(
            client, groups["sg-"],
            "DescribeSecurityGroups", models.DescribeSecurityGroupsRequest,
            "SecurityGroupIds", "SecurityGroupSet", "SecurityGroupId", "SecurityGroupName",
        ))

    # EIPs
    if groups["eip-"]:
        result.update(_fetch_by_ids(
            client, groups["eip-"],
            "DescribeAddresses", models.DescribeAddressesRequest,
            "AddressIds", "AddressSet", "AddressId", "AddressName",
        ))

    # IPv6 EIPs
    if groups["eipv6-"]:
        result.update(_fetch_by_ids(
            client, groups["eipv6-"],
            "DescribeIp6Addresses", models.DescribeIp6AddressesRequest,
            "Ip6AddressIds", "AddressSet", "AddressId", "AddressName",
        ))

    # Route Tables
    if groups["rtb-"]:
        result.update(_fetch_by_ids(
            client, groups["rtb-"],
            "DescribeRouteTables", models.DescribeRouteTablesRequest,
            "RouteTableIds", "RouteTableSet", "RouteTableId", "RouteTableName",
        ))

    # Address Templates (IP parameter templates)
    if groups["ipm-"]:
        try:
            for i in range(0, len(groups["ipm-"]), 100):
                batch = groups["ipm-"][i:i + 100]
                req = models.DescribeAddressTemplatesRequest()
                req.from_json_string(json.dumps({
                    "Filters": [{"Name": "address-template-id", "Values": batch}],
                    "Limit": "100",
                }))
                resp = client.DescribeAddressTemplates(req)
                for tpl in (resp.AddressTemplateSet or []):
                    result[tpl.AddressTemplateId] = {
                        "ResourceType": "address-template",
                        "PaymentModel": "",
                        "Status": "",
                        "Name": tpl.AddressTemplateName or "",
                        "CreationDate": getattr(tpl, "CreatedTime", "") or "",
                    }
        except TencentCloudSDKException as e:
            print(f"  [WARN] VPC DescribeAddressTemplates error: {e}")

    # Address Template Groups (IP parameter template groups)
    if groups["ipmg-"]:
        try:
            for i in range(0, len(groups["ipmg-"]), 100):
                batch = groups["ipmg-"][i:i + 100]
                req = models.DescribeAddressTemplateGroupsRequest()
                req.from_json_string(json.dumps({
                    "Filters": [{"Name": "address-template-group-id", "Values": batch}],
                    "Limit": "100",
                }))
                resp = client.DescribeAddressTemplateGroups(req)
                for grp in (resp.AddressTemplateGroupSet or []):
                    result[grp.AddressTemplateGroupId] = {
                        "ResourceType": "address-template-group",
                        "PaymentModel": "",
                        "Status": "",
                        "Name": grp.AddressTemplateGroupName or "",
                        "CreationDate": getattr(grp, "CreatedTime", "") or "",
                    }
        except TencentCloudSDKException as e:
            print(f"  [WARN] VPC DescribeAddressTemplateGroups error: {e}")

    # Keep unknown-prefix resources (don't flag as ghost)
    for rid in other:
        result[rid] = {
            "ResourceType": "",
            "PaymentModel": "",
            "Status": "",
            "Name": "",
            "CreationDate": "",
        }

    found = len(result)
    ghost = len(resource_ids) - found
    if ghost:
        ghost_ids = [rid for rid in resource_ids if rid not in result]
        print(f"  [VPC] {found} valid, {ghost} ghost resources: {ghost_ids[:5]}{'...' if ghost > 5 else ''}")

    return result
