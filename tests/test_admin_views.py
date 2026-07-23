import pytest
from app.admin.views import admin_views

class TestAdminViews:
    def test_admin_views_configuration(self) -> None:
        """
        Validates that all Admin ModelViews are configured correctly
        and their mapped columns actually exist on the SQLAlchemy models.
        """
        for view_class in admin_views:
            # Ensure a model is attached
            assert hasattr(view_class, "model")
            model = view_class.model
            
            # Check column_list mapping
            if hasattr(view_class, "column_list"):
                for col in view_class.column_list:
                    # In sqladmin, column_list items can be strings or InstrumentAttributes
                    if isinstance(col, str):
                        assert hasattr(model, col), f"Column {col} missing on {model.__name__}"
            
            # Check column_searchable_list mapping
            if hasattr(view_class, "column_searchable_list"):
                for col in view_class.column_searchable_list:
                    if isinstance(col, str):
                        assert hasattr(model, col), f"Searchable Column {col} missing on {model.__name__}"
            
            # Check column_sortable_list mapping
            if hasattr(view_class, "column_sortable_list"):
                for col in view_class.column_sortable_list:
                    if isinstance(col, str):
                        assert hasattr(model, col), f"Sortable Column {col} missing on {model.__name__}"

    def test_admin_views_registered_count(self) -> None:
        """
        Ensure we don't accidentally drop admin views.
        """
        assert len(admin_views) >= 9
