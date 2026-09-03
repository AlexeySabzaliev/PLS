"""Тест cleanup-reference-real (dry-run)."""
from app.seeds.cleanup_reference_real import cleanup_reference_real


def test_cleanup_reference_real_dry_run(app):
    with app.app_context():
        report = cleanup_reference_real(dry_run=True, force=True, skip_backup=True)
    assert any("cleanup-reference-real" in line for line in report.actions)
