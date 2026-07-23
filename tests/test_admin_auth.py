import pytest
from unittest.mock import AsyncMock, patch

from app.admin.auth import AdminAuth


class TestAdminAuth:
    @pytest.mark.asyncio
    async def test_login_success(self) -> None:
        mock_request = AsyncMock()
        mock_request.form.return_value = {"username": "admin", "password": "test_admin_secret"}
        mock_request.session = {}

        with patch("app.admin.auth.settings") as mock_settings:
            mock_settings.ADMIN_SECRET_KEY = "test_admin_secret"
            auth = AdminAuth(secret_key="secret")
            
            result = await auth.login(mock_request)
            
            assert result is True
            assert mock_request.session.get("authenticated") is True

    @pytest.mark.asyncio
    async def test_login_failure(self) -> None:
        mock_request = AsyncMock()
        mock_request.form.return_value = {"username": "admin", "password": "wrong_password"}
        mock_request.session = {}

        with patch("app.admin.auth.settings") as mock_settings:
            mock_settings.ADMIN_SECRET_KEY = "test_admin_secret"
            auth = AdminAuth(secret_key="secret")
            
            result = await auth.login(mock_request)
            
            assert result is False
            assert "authenticated" not in mock_request.session

    @pytest.mark.asyncio
    async def test_logout(self) -> None:
        mock_request = AsyncMock()
        mock_request.session = {"authenticated": True}

        auth = AdminAuth(secret_key="secret")
        result = await auth.logout(mock_request)
        
        assert result is True
        assert mock_request.session == {}

    @pytest.mark.asyncio
    async def test_authenticate_success(self) -> None:
        mock_request = AsyncMock()
        mock_request.session = {"authenticated": True}

        auth = AdminAuth(secret_key="secret")
        result = await auth.authenticate(mock_request)
        
        assert result is True

    @pytest.mark.asyncio
    async def test_authenticate_failure(self) -> None:
        mock_request = AsyncMock()
        mock_request.session = {}

        auth = AdminAuth(secret_key="secret")
        result = await auth.authenticate(mock_request)
        
        assert result is False
