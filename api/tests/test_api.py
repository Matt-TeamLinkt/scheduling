"""The whole scheduler flow through HTTP, on a temporary database."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from scheduling_engine import Event, League, validate

from scheduling_api.main import create_app


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(f"sqlite:///{tmp_path / 'test.db'}")) as c:
        yield c


def wait(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(600):
        j: dict[str, Any] = client.get(f"/api/jobs/{job_id}").json()
        if j["state"] != "running":
            return j
        time.sleep(0.1)
    raise AssertionError("job never finished")


def generated(client: TestClient, sample: str = "small_8") -> dict[str, Any]:
    s = client.post("/api/seasons", json={"name": "Spring", "sample": sample}).json()
    job = client.post(f"/api/seasons/{s['id']}/generate", json={"seconds": 8}).json()
    j = wait(client, job["job_id"])
    assert j["state"] == "done", j
    out: dict[str, Any] = client.get(f"/api/seasons/{s['id']}").json()
    return out


def test_generate_a_sample_league(client: TestClient) -> None:
    s = generated(client)
    assert len(s["events"]) == 28 and s["unplaced"] == []
    lg = League.model_validate(s["league"])
    assert validate(lg, [Event.model_validate(e) for e in s["events"]]) == []
    assert s["last_action"] == "Generated the schedule"
    assert s["unpublished_changes"] == 28
    assert [g["label"] for g in s["goals"]][0] == "Share early and late games fairly"


def test_import_into_a_new_season(client: TestClient) -> None:
    s = client.post(
        "/api/seasons",
        json={
            "name": "Fall",
            "sport": "soccer",
            "season_start": "2027-09-04",
            "season_end": "2027-11-14",
        },
    ).json()
    sid = s["id"]
    teams = (
        b"Team,Division,Coach\nFalcons,U10,Alex Ramsey\nRovers,U10,Sam Diaz\n"
        b"Comets,U10,Alex Ramsey\nKings,U10,Pat Kim\n"
    )
    pv = client.post(
        f"/api/seasons/{sid}/import/teams",
        files={"file": ("t.csv", teams)},
        data={"apply": "false"},
    ).json()
    assert pv["counts"]["teams"] == 4 and "season" not in pv
    out = client.post(
        f"/api/seasons/{sid}/import/teams", files={"file": ("t.csv", teams)}, data={"apply": "true"}
    ).json()
    assert len(out["season"]["league"]["teams"]) == 4
    slots = b"Venue,Date,Start,End\n" + b"".join(
        f"Maple Park,2027-09-{d:02d},{h}:00,{h + 1}:00\n".encode()
        for d in (4, 11, 18, 25)
        for h in (9, 10)
    )
    out = client.post(
        f"/api/seasons/{sid}/import/slots", files={"file": ("s.csv", slots)}, data={"apply": "true"}
    ).json()
    assert len(out["season"]["league"]["slots"]) == 8
    check = client.get(f"/api/seasons/{sid}/setup-check").json()
    assert check["problems"] == []
    assert check["capacity"]  # 10 games each on 4 Saturdays can't work: it says so


def test_check_move_undo_redo(client: TestClient) -> None:
    s = generated(client)
    sid = s["id"]
    a, b = s["events"][0], s["events"][1]
    # Dropping a onto b's spot: a problem, explained.
    clash = client.post(
        f"/api/seasons/{sid}/check",
        json={"event_id": a["id"], "slot_id": b["slot_id"], "start": b["start"]},
    ).json()
    if a["slot_id"] != b["slot_id"] or a["start"] != b["start"]:
        assert not clash["ok"] and clash["problems"]
    # Find an empty legal slot for a.
    lg = League.model_validate(s["league"])
    used = {(e["slot_id"]) for e in s["events"]}
    target = None
    for sl in lg.slots:
        if sl.id in used:
            continue
        r = client.post(
            f"/api/seasons/{sid}/check",
            json={
                "event_id": a["id"],
                "slot_id": sl.id,
                "start": datetime.combine(sl.date, sl.start).isoformat(),
            },
        ).json()
        if r["ok"]:
            target = sl
            break
    assert target is not None
    moved = client.post(
        f"/api/seasons/{sid}/move",
        json={
            "event_id": a["id"],
            "slot_id": target.id,
            "start": datetime.combine(target.date, target.start).isoformat(),
        },
    ).json()
    assert moved["problems"] == [] and moved["can_undo"]
    assert moved["last_action"].startswith("Moved ")
    back = client.post(f"/api/seasons/{sid}/undo").json()
    assert back["message"].startswith("Undid: Moved ")
    assert next(e for e in back["events"] if e["id"] == a["id"])["slot_id"] == a["slot_id"]
    again = client.post(f"/api/seasons/{sid}/redo").json()
    assert next(e for e in again["events"] if e["id"] == a["id"])["slot_id"] == target.id
    assert client.post(f"/api/seasons/{sid}/redo").status_code == 400


def test_publish_and_change_log(client: TestClient) -> None:
    s = generated(client)
    sid = s["id"]
    pub = client.post(f"/api/seasons/{sid}/publish").json()
    assert pub["published_version"] == pub["version"]
    assert len(pub["publication"]["changes"]) == 28
    assert pub["unpublished_changes"] == 0
    # Lock a game: no schedule change, nothing new to tell families.
    e = s["events"][0]
    locked = client.post(f"/api/seasons/{sid}/events/{e['id']}/lock", json={"locked": True}).json()
    assert next(x for x in locked["events"] if x["id"] == e["id"])["locked"]
    assert client.get(f"/api/seasons/{sid}/publish-preview").json()["changes"] == []
    history = client.get(f"/api/seasons/{sid}/publications").json()
    assert len(history) == 1


def test_report_explain_and_clone(client: TestClient) -> None:
    s = generated(client)
    sid = s["id"]
    rep = client.get(f"/api/seasons/{sid}/report").json()
    assert len(rep["teams"]) == 8 and "summary" in rep
    ex = client.get(f"/api/seasons/{sid}/explain").json()
    assert ex["summary"] == "Every game fits."
    c = client.post(
        f"/api/seasons/{sid}/clone", json={"name": "Next spring", "season_start": "2028-04-08"}
    ).json()
    lg = League.model_validate(c["league"])
    assert lg.season_start.isoformat() == "2028-04-08" and c["events"] == []
    assert all(sl.date.weekday() == 5 for sl in lg.slots)  # still Saturdays


def test_missing_season(client: TestClient) -> None:
    r = client.get("/api/seasons/nope")
    assert r.status_code == 404 and r.json()["detail"] == "That season doesn't exist."


def test_matchups_only_then_place_by_hand(client: TestClient) -> None:
    s = client.post("/api/seasons", json={"name": "Spring", "sample": "small_8"}).json()
    sid = s["id"]
    job = client.post(f"/api/seasons/{sid}/generate", json={"matchups_only": True}).json()
    j = wait(client, job["job_id"])
    assert j["state"] == "done" and "Needs a spot" in j["result"]["summary"]
    s = client.get(f"/api/seasons/{sid}").json()
    assert s["events"] == [] and len(s["unplaced"]) == 28
    assert s["last_action"] == "Built the matchups"

    mid = s["unplaced"][0]["id"]
    spots = client.get(f"/api/seasons/{sid}/unplaced/{mid}/spots").json()
    assert spots and spots[0]["suggested"] and spots[0]["problems"] == []
    best = spots[0]
    to_best = {"event_id": mid, "slot_id": best["slot_id"], "start": best["start"]}
    ok = client.post(f"/api/seasons/{sid}/check", json=to_best).json()
    assert ok == {"ok": True, "problems": []}
    s = client.post(f"/api/seasons/{sid}/move", json=to_best).json()
    assert len(s["events"]) == 1 and len(s["unplaced"]) == 27
    assert s["last_action"].startswith("Placed ")

    # Back to the tray, and undo brings it back to the schedule.
    s = client.post(f"/api/seasons/{sid}/events/{mid}/unschedule").json()
    assert s["events"] == [] and len(s["unplaced"]) == 28
    assert s["last_action"].startswith("Took ")
    s = client.post(f"/api/seasons/{sid}/undo").json()
    assert len(s["events"]) == 1

    assert client.get(f"/api/seasons/{sid}/unplaced/nope/spots").status_code == 404
