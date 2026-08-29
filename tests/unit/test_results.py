from src.domain.shared.results import SyncReport


def test_a_clean_run_is_ok():
    report = SyncReport(entity="deputy", processed=100, created=100)
    assert report.ok is True


def test_a_few_failures_are_tolerated():
    report = SyncReport(entity="deputy", processed=100, created=95, failed=5)
    assert report.ok is True


def test_too_many_failures_raise_the_alarm():
    """Au-delà de 20 % d'échecs, la source a probablement changé de format."""
    report = SyncReport(entity="deputy", processed=100, created=70, failed=30)
    assert report.ok is False


def test_processing_nothing_is_not_a_success():
    """Un run vide est un symptôme, pas un succès : il doit sortir en échec."""
    assert SyncReport(entity="deputy").ok is False


def test_error_sample_stays_bounded():
    report = SyncReport(entity="deputy")
    for i in range(100):
        report.record_failure(f"PA{i}")

    assert report.failed == 100
    assert len(report.errors) == SyncReport.ERROR_SAMPLE_SIZE


def test_as_dict_is_serialisable():
    report = SyncReport(entity="law", processed=3, created=3).finish()
    payload = report.as_dict()

    assert payload["entity"] == "law"
    assert payload["ok"] is True
    assert payload["duration_s"] is not None
    assert isinstance(payload["started_at"], str)
