from dmarc_metrics_exporter.expiring_set import ExpiringSet


def test_containment_with_ttl():
    current_time = 0

    expiring_set = ExpiringSet(1, lambda: current_time)
    assert "a" not in expiring_set
    expiring_set.add("a")
    assert "a" in expiring_set
    current_time += 1
    assert "a" not in expiring_set
