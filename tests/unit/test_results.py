from src.domain.shared.results import SyncReport


def test_a_clean_run_is_ok():
    report = SyncReport(entity="deputy", processed=100, created=100)
    assert report.ok is True


def test_a_few_failures_are_tolerated():
    report = SyncReport(entity="deputy", processed=100, created=95, failed=5)
    assert report.ok is True


def test_too_many_failures_raise_the_alarm():
    """Past 20% failures the source has probably changed format."""
    report = SyncReport(entity="deputy", processed=100, created=70, failed=30)
    assert report.ok is False


def test_processing_nothing_is_not_a_success():
    """An empty run is a symptom, not a success."""
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
