from dmarc_metrics_exporter.expiring_set import ExpiringSet


def test_containment_with_ttl():
    current_time = 0

    expiring_set = ExpiringSet(1, lambda: current_time)
    assert "a" not in expiring_set
    expiring_set.add("a")
    assert "a" in expiring_set
    current_time += 1
    assert "a" not in expiring_set


def test_roundtrip_persistence(tmp_path):
    current_time = 0
    filepath = tmp_path / "seen_reports.db"

    expiring_set = ExpiringSet(3, lambda: current_time)
    expiring_set.add("t0")
    current_time += 1
    expiring_set.add("t1")
    current_time += 1
    expiring_set.add("t2")
    current_time += 1
    expiring_set.persist(filepath)

    expiring_set = ExpiringSet.load(filepath, 3, lambda: current_time)
    assert "t0" not in expiring_set
    assert "t1" in expiring_set
    assert "t2" in expiring_set
    current_time += 1
    assert "t1" not in expiring_set
    assert "t2" in expiring_set
