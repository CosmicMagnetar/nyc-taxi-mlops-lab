"""predict_duration and query_zone_stats, with serving and the warehouse faked."""

import json

import pytest

import labmcp.server as s


async def test_predict_duration_sends_features_yamls_encodings(monkeypatch):
    seen = []

    async def champion(method, path, body=None):
        seen.append((method, path, body))
        return {"duration_minutes": 41.5, "model": {"name": "trip-duration", "version": "1", "alias": "champion"}}

    monkeypatch.setattr(s, "champion", champion)
    out = json.loads((await s.mcp.call_tool("predict_duration", {"pickup_zone": "JFK Airport", "dropoff_zone": "Times Sq/Theatre District",
                                                                   "hour": 17, "day_of_week": "friday"}))[0].text)
    assert seen == [("POST", "/predict", {"pickup_zone_id": 132, "dropoff_zone_id": 230, "pickup_hour": 17, "pickup_dow": 5})]
    assert out["duration_minutes"] == 41.5 and out["model"]["alias"] == "champion"


async def test_predict_duration_unknown_zone_is_an_error_with_suggestions(monkeypatch):
    async def champion(*a, **k):
        raise AssertionError("serving must not be called for an unknown zone")

    monkeypatch.setattr(s, "champion", champion)
    with pytest.raises(Exception, match="did you mean"):
        await s.mcp.call_tool("predict_duration", {"pickup_zone": "JFK Airprot", "dropoff_zone": "Times Sq/Theatre District",
                                                    "hour": 17, "day_of_week": "friday"})


class FakeWarehouse:
    calls: list = []

    def query(self, sql, params=None, timeout_s=30):
        FakeWarehouse.calls.append((sql, params))
        return [{"pickup_hour": "17", "value": 18.2, "first_month": "2024-01", "last_month": "2024-03"}]


def test_query_zone_stats_binds_parameters_and_never_formats_input(monkeypatch):
    FakeWarehouse.calls = []
    monkeypatch.setattr(s, "Warehouse", FakeWarehouse)
    out = s.query_zone_stats("JFK Airport", "median_duration_min", 17)
    sql, params = FakeWarehouse.calls[0]
    assert params == {"zone": 132, "hour": 17}
    assert ":zone" in sql and ":hour" in sql and "JFK" not in sql and "132" not in sql and "median_duration_min as value" in sql
    assert out["by_hour"] == [{"hour": 17, "value": 18.2}] and out["months"] == "2024-01..2024-03"


def test_query_zone_stats_refuses_injection_in_the_zone_and_the_metric(monkeypatch):
    monkeypatch.setattr(s, "Warehouse", FakeWarehouse)
    FakeWarehouse.calls = []
    with pytest.raises(ValueError, match="unknown TLC zone"):
        s.query_zone_stats("JFK Airport'; drop table marts.zone_hour_stats; --", "trip_count")
    with pytest.raises(ValueError, match="unknown metric"):
        s.query_zone_stats("JFK Airport", "trip_count; select * from ingest.trips")
    assert FakeWarehouse.calls == []
