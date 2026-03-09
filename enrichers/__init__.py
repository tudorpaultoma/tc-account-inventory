from .cvm import enrich_cvm
from .cbs import enrich_cbs
from .clb import enrich_clb
from .mysql import enrich_mysql
from .redis_enrich import enrich_redis
from .generic import enrich_generic
from .gaap import enrich_gaap
from .vpc import enrich_vpc
from .autoscaling import enrich_autoscaling
from .cam import enrich_cam
from .tke import enrich_tke
from .ssl_cert import enrich_ssl
from .scf import enrich_scf
from .cls_enrich import enrich_cls
from .lighthouse_enrich import enrich_lighthouse
from .apigw import enrich_apigw
from .cos import enrich_cos
from .tat_enrich import enrich_tat
from .tione_enrich import enrich_tione
from .privatedns_enrich import enrich_privatedns
from .live_enrich import enrich_live
from .monitor_enrich import enrich_monitor
from .vod_enrich import enrich_vod
from .organization_enrich import enrich_organization
from .rum_enrich import enrich_rum
from .ctsdb_enrich import enrich_ctsdb

# Map ServiceType -> enricher function
ENRICHERS = {
    "cvm": enrich_cvm,
    "cbs": enrich_cbs,
    "clb": enrich_clb,
    "cdb": enrich_mysql,
    "redis": enrich_redis,
    "gaap": enrich_gaap,
    "vpc": enrich_vpc,
    "as": enrich_autoscaling,
    "cam": enrich_cam,
    "tke": enrich_tke,
    "ssl": enrich_ssl,
    "scf": enrich_scf,
    "cls": enrich_cls,
    "lighthouse": enrich_lighthouse,
    "apigw": enrich_apigw,
    "cos": enrich_cos,
    "tat": enrich_tat,
    "tione": enrich_tione,
    "privatedns": enrich_privatedns,
    "live": enrich_live,
    "monitor": enrich_monitor,
    "vod": enrich_vod,
    "organization": enrich_organization,
    "rum": enrich_rum,
    "ctsdb": enrich_ctsdb,
}


def get_enricher(service_type):
    return ENRICHERS.get(service_type, enrich_generic)
