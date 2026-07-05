from __future__ import annotations

from . import (
    ashby,
    bamboohr,
    generic_jsonld,
    greenhouse,
    lever,
    recruitee,
    smartrecruiters,
    workable,
)


ADAPTERS = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "smartrecruiters": smartrecruiters.fetch,
    "workable": workable.fetch,
    "recruitee": recruitee.fetch,
    "bamboohr": bamboohr.fetch,
    "generic_jsonld": generic_jsonld.fetch,
}
