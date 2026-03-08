from .cvm import enrich_cvm
from .cbs import enrich_cbs
from .clb import enrich_clb
from .mysql import enrich_mysql
from .redis_enrich import enrich_redis
from .generic import enrich_generic

# Map ServiceType -> enricher function
ENRICHERS = {
    "cvm": enrich_cvm,
    "cbs": enrich_cbs,
    "clb": enrich_clb,
    "cdb": enrich_mysql,
    "redis": enrich_redis,
}


def get_enricher(service_type):
    return ENRICHERS.get(service_type, enrich_generic)
