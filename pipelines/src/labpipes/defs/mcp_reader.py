"""S7: the MCP server's database user. query_zone_stats must not run as labadmin: this creates a user that
can read marts.zone_hour_stats and nothing else (decision 018), with the RedshiftData resource.
The MCP server connects as it through the Data API's --db-user path (MCP_DB_USER, default lab_ro), so it
needs no password: the user is created with `password disable`.

The grants survive the mart's refresh: zone_hour_stats.sql rebuilds the table with `delete` and `insert`
(the table is never dropped), and a grant is attached to the table, not to its rows. They are given on
the one table, with no default privileges, so a new table in marts is not readable until someone decides it should be.

Run it by hand: scripts/dagster-run.sh mcp_reader_job --wait (after zone_hour_stats has run once).
"""

import dagster as dg

from ..resources import RedshiftData
from .marts import zone_hour_stats

DB_USER = "lab_ro"  # constant, never from input: it is formatted into DDL below
STATEMENT_TIMEOUT_MS = 30000

PRIVILEGE_CHECK = (
    "select has_table_privilege('{u}', 'marts.zone_hour_stats', 'select') as read_marts,"
    " has_table_privilege('{u}', 'marts.zone_hour_stats', 'insert') as write_marts,"
    " has_table_privilege('{u}', 'marts.zone_hour_stats', 'delete') as delete_marts,"
    " has_schema_privilege('{u}', 'marts', 'create') as create_in_marts,"
    " has_schema_privilege('{u}', 'ingest', 'usage') as use_ingest,"
    " has_schema_privilege('{u}', 'staging', 'usage') as use_staging"
).format(u=DB_USER)

EXPECTED = {
    "read_marts": True,
    "write_marts": False,
    "delete_marts": False,
    "create_in_marts": False,
    "use_ingest": False,
    "use_staging": False,
}


def _truthy(v) -> bool:
    return v in (True, "true", "t", 1, "1")


@dg.asset(deps=[zone_hour_stats], group_name="marts", kinds={"redshift"}, pool="redshift")
def mcp_reader(redshift: RedshiftData) -> dg.MaterializeResult:
    exists = int(redshift.scalar(f"select count(*) from pg_user where usename = '{DB_USER}'"))
    redshift.execute(
        *([] if exists else [f"create user {DB_USER} password disable"]),
        f"alter user {DB_USER} set statement_timeout to {STATEMENT_TIMEOUT_MS}",
        f"alter user {DB_USER} connection limit 5",
        # Start from nothing on the schemas the pipeline owns, then give exactly one thing back.
        f"revoke all on schema ingest from {DB_USER}",
        f"revoke all on schema staging from {DB_USER}",
        f"revoke all on all tables in schema marts from {DB_USER}",
        f"grant usage on schema marts to {DB_USER}",
        f"grant select on marts.zone_hour_stats to {DB_USER}",
    )
    row = redshift.query(PRIVILEGE_CHECK)[0]
    got = {k: _truthy(v) for k, v in row.items()}
    wrong = {k: got.get(k) for k, want in EXPECTED.items() if got.get(k) != want}
    if wrong:
        raise dg.Failure(f"{DB_USER} has the wrong privileges: {wrong}")
    return dg.MaterializeResult(metadata={"db_user": DB_USER, **{k: dg.MetadataValue.bool(v) for k, v in got.items()}})


mcp_reader_job = dg.define_asset_job("mcp_reader_job", selection=dg.AssetSelection.assets(mcp_reader))
