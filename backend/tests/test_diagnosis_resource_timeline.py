from DiagnosisModule.diagnosis_service import StudentDiagnosisService


def resource(at, path="data/Book/1.PDF", **kwargs):
    return {"type": "resource_learning", "node_id": "lifecycle", "resource_path": path,
            "event_type": "view", "progress_percent": 5, "occurred_at": at, **kwargs}


def test_nearby_opens_merge_but_other_resources_and_later_sessions_remain():
    rows = [resource("2026-10-08T17:57:20"), resource("2026-10-08T17:56:20"),
            resource("2026-10-08T17:57:19", "https://www.youtube.com/watch?v=abc"),
            resource("2026-10-08T16:50:00"), resource("2026-10-08T17:57:30", event_type="complete", is_completed=True)]
    merged = StudentDiagnosisService._merge_resource_timeline(rows)
    assert len(merged) == 4
    opened = next(row for row in merged if row["occurred_at"] == "2026-10-08T17:57:20")
    assert opened["event_count"] == 2
    service = StudentDiagnosisService.__new__(StudentDiagnosisService)
    safe = service._student_evidence_timeline(merged)
    assert any("YouTube" in row["summary"] for row in safe)
    assert "5%" not in next(row["summary"] for row in safe if row["occurred_at"] == opened["occurred_at"])
    assert all("resource_path" in row for row in safe)


def test_heartbeat_duration_is_not_summed_and_progress_keeps_maximum():
    rows = [resource("2026-10-08T17:57:00", event_type="progress", progress_percent=40, duration_seconds=90),
            resource("2026-10-08T17:56:00", event_type="progress", progress_percent=20, duration_seconds=30)]
    merged = StudentDiagnosisService._merge_resource_timeline(rows)
    assert len(merged) == 1
    assert merged[0]["duration_seconds"] == 90
    assert merged[0]["progress_percent"] == 40
