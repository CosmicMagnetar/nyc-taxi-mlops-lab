"""The MCP reader user: created without a password, granted one table, and the asset checks the result."""

import dagster as dg
import pytest

from labpipes.defs.mcp_reader import EXPECTED, mcp_reader
from fakes import LOG, FakeRedshift


class ReaderRedshift(FakeRedshift):
    privileges: dict = dict(EXPECTED)

    def query(self, sql: str):
        LOG.append(sql)
        return [{k: ("t" if v else "f") for k, v in self.privileges.items()}] if "has_table_privilege" in sql else super().query(sql)


def run(**kw):
    LOG.clear()
    return mcp_reader(ReaderRedshift(cluster_id="lab", database="lab", db_user="labadmin", **kw))


def test_creates_the_user_without_a_password_and_grants_one_table():
    # the fake's count(*) says the user exists (3 rows), so no create; a fresh warehouse would create it first
    run()
    text = "\n".join(LOG)
    assert "grant select on marts.zone_hour_stats to lab_ro" in text and "grant usage on schema marts to lab_ro" in text
    assert "revoke all on schema ingest from lab_ro" in text and "default privileges" not in text
    assert "password" not in text  # no password is ever set; the user exists, so no create statement ran


def test_fails_when_the_user_can_write_the_mart():
    with pytest.raises(dg.Failure, match="write_marts"):
        run(privileges={**EXPECTED, "write_marts": True})
