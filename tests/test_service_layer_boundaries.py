from pathlib import Path
from unittest import TestCase


class ServiceLayerBoundaryTests(TestCase):
    def test_services_do_not_access_the_database_session_directly(self) -> None:
        services_root = Path(__file__).resolve().parents[1] / "app" / "services"
        allowed_session_owners = {
            services_root / "base.py",
            services_root / "business" / "base.py",
        }

        violations: list[str] = []
        for source_file in services_root.rglob("*.py"):
            if source_file in allowed_session_owners:
                continue
            source = source_file.read_text(encoding="utf-8")
            if "self.session" in source or "_get_session(" in source:
                violations.append(str(source_file.relative_to(services_root)))

        self.assertEqual(
            violations,
            [],
            "Only the base service classes may own an AsyncSession; "
            "other services must call repositories.",
        )
