"""Recompute public marginal identities, without claiming to recheck private acquisition."""
from collections import defaultdict
from . import disclosure, frozen
from .common import read_csv, load_json, SITE_IDS, HTTP_METHODS, IDENTITY_TIERS, ACTOR_ROLES


def reconcile_tables(directory):
    tables = disclosure.tables(directory)
    resources = {r["resource_id"]:r for r in tables["resources"]}
    cells = tables["consultations"]
    valid = all(r["resource_id"] in resources and r["site_id"] in SITE_IDS and r["http_method"] in HTTP_METHODS
                and r["actor_role"] in ACTOR_ROLES and r["stored_identity_tier"] in IDENTITY_TIERS
                and r["http_status"].isdigit() and 100 <= int(r["http_status"]) <= 599
                and (r["site_id"],r["path"]) == (resources[r["resource_id"]]["site_id"],resources[r["resource_id"]]["path"]) for r in cells)
    if not valid:
        return {"public_cell_references_domains_and_types":False}
    def population(resource):
        return "main_documentary" if resource["main_population"] == "true" else {"control_resource":"robots_control","undeclared_bucket":"undeclared_bucket"}.get(resource["scope_class"],"other_documentary")
    expected_actor = defaultdict(lambda:[0,0,set()]); per_resource=defaultdict(lambda:[0,0,0,0,0,0])
    expected_family = defaultdict(int); expected_daily=defaultdict(int)
    policy=load_json(frozen.rule_path(directory.name,"small-cell-policy.json"))
    for row in cells:
        n=int(row["request_count"]);rid=row["resource_id"];resource=resources[rid];pop=population(resource)
        get=row["http_method"]=="GET" and row["http_status"]=="200"
        ai=get and row["stored_identity_tier"]=="provider_origin_verified_actor" and row["actor_role"] in ("ai_training","ai_search","user_initiated_fetch")
        key=(pop,)+tuple(row[k] for k in ("site_id","actor_family","actor_name","actor_role","stored_identity_tier","attribution_assessment"))
        a=expected_actor[key];a[0]+=n;a[1]+=n if get else 0;a[2].add(row["path"])
        flags=(True,get,row["http_method"]=="HEAD",row["http_status"]=="304",int(row["http_status"])>=400,ai)
        for i,flag in enumerate(flags):per_resource[rid][i]+=n if flag else 0
        if ai and row["actor_role"] in ("ai_training","ai_search") and pop=="main_documentary":
            expected_family[(resource["family"],row["actor_role"])]+=n
        if not disclosure.protected(row,policy):
            expected_daily[(row["site_id"],pop,row["actor_role"],row["stored_identity_tier"],row["http_method"],row["http_status"])]+=n
    actual_actor={tuple(r[k] for k in ("population","site_id","actor_family","actor_name","actor_role","stored_identity_tier","attribution_assessment")):[int(r["requests"]),int(r["get200"]),int(r["distinct_paths_in_group"])] for r in tables["actors"]}
    expected_actor={k:[a,b,len(c)] for k,(a,b,c) in expected_actor.items()}
    fields=("requests_all_actors","get200_all_actors","head_all_actors","status304_all_actors","status4xx5xx_all_actors","provider_origin_ai_get200")
    actual_resource={r["resource_id"]:[int(r[k]) for k in fields] for r in tables["resource_summary"]}
    actual_family=defaultdict(int)
    for r in tables["family_daily"]:
        if r["request_count"] != "":actual_family[(r["family"],r["actor_role"])]+=int(r["request_count"])
    actual_daily=defaultdict(int)
    for r in tables["daily"]:
        if not disclosure.protected(r,policy):
            actual_daily[tuple(r[k] for k in ("site_id","population","actor_role","stored_identity_tier","http_method","http_status"))]+=int(r["request_count"])
    nonzero=lambda d:{k:v for k,v in d.items() if v}
    return {"public_cell_references_domains_and_types":True,"public_actor_marginals_recomputed":actual_actor==expected_actor,
            "public_resource_marginals_recomputed":actual_resource==dict(per_resource),
            "public_family_role_marginals_recomputed":nonzero(actual_family)==nonzero(expected_family),
            "public_daily_nonprotected_stratum_marginals_recomputed":nonzero(actual_daily)==nonzero(expected_daily)}
