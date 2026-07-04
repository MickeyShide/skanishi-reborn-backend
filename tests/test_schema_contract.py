from pathlib import Path
from unittest import TestCase

from sqlalchemy import CHAR

from app.db.models.item import Item
from app.db.models.item_image import ItemImage
from app.db.models.item_secrets import ItemSecret
from app.db.models.prototype import Prototype
from app.db.models.refresh_session import RefreshSession
from app.db.models.validation import Validation


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "20260704_0003_align_schema_contract.py"
)


class ModelSchemaContractTests(TestCase):
    def test_hash_columns_use_char_64(self) -> None:
        self.assertIsInstance(RefreshSession.__table__.c.token_hash.type, CHAR)
        self.assertEqual(RefreshSession.__table__.c.token_hash.type.length, 64)
        self.assertIsInstance(ItemSecret.__table__.c.secret_hash.type, CHAR)
        self.assertEqual(ItemSecret.__table__.c.secret_hash.type.length, 64)

    def test_foreign_keys_are_named_explicitly(self) -> None:
        tables = [
            RefreshSession.__table__,
            Prototype.__table__,
            Item.__table__,
            ItemImage.__table__,
            ItemSecret.__table__,
            Validation.__table__,
        ]

        for table in tables:
            for constraint in table.foreign_key_constraints:
                self.assertTrue(
                    constraint.name,
                    f"Foreign key in table {table.name} must have an explicit name.",
                )


class MigrationContractTests(TestCase):
    def test_reconciliation_migration_updates_existing_schema(self) -> None:
        content = MIGRATION_PATH.read_text(encoding="utf-8")

        self.assertIn("op.alter_column(", content)
        self.assertIn("token_hash::char(64)", content)
        self.assertIn("secret_hash::char(64)", content)
        self.assertIn("fk_refresh_sessions_user_id_users", content)
        self.assertIn(
            "fk_refresh_sessions_replaced_by_session_id_refresh_sessions",
            content,
        )
        self.assertIn("fk_prototypes_type_id_types", content)
        self.assertIn("fk_items_category_id_categories", content)
        self.assertIn("fk_items_prototype_id_prototypes", content)
        self.assertIn("fk_items_type_id_types", content)
        self.assertIn("fk_item_images_item_id_items", content)
        self.assertIn("fk_item_secrets_item_id_items", content)
        self.assertIn("fk_validations_user_id_users", content)
        self.assertIn("fk_validations_item_id_items", content)
        self.assertIn("fk_validations_item_secret_id_item_secrets", content)
