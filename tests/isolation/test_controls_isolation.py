"""Comprehensive tenant isolation tests for Controls endpoints."""

import pytest
from fastapi import status
from uuid import uuid4

from auth.jwt import create_dev_token


class TestControlsListIsolation:
    """Test GET /api/v1/controls isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/v1/controls", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_invalid_membership_id_returns_400_or_403(
        self, client, tenant_a, user_tenant_a
    ):
        """Invalid membership ID returns 400 or 403."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": "not-a-uuid",
        }
        
        response = client.get("/api/v1/controls", headers=headers)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]
    
    @pytest.mark.asyncio
    async def test_membership_id_for_different_user_returns_403(
        self, client, tenant_a, user_tenant_a, user_tenant_b
    ):
        """Membership ID belonging to a different user returns 403."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_b.id),
        }
        
        response = client.get("/api/v1/controls", headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_cross_tenant_read_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """User in Tenant A cannot see Tenant B's controls."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User B creates a control in Tenant B
        token_b = create_dev_token(
            user_id=user_b.id,
            tenant_id=tenant_b.id,
            role=membership_b.role,
            is_platform_admin=False,
        )
        headers_b = {
            "Authorization": f"Bearer {token_b}",
            "X-Membership-Id": str(membership_b.id),
        }
        
        control_data = {
            "control_code": "AC-001",
            "name": "Tenant B Control",
            "is_key": False,
            "is_automated": False,
        }
        response = client.post("/api/v1/controls", json=control_data, headers=headers_b)
        assert response.status_code == status.HTTP_200_OK
        control_b = response.json()
        control_b_id = control_b["id"]
        
        # User A tries to list controls - should not see Tenant B's control
        token_a = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Membership-Id": str(membership_a.id),
        }
        
        response = client.get("/api/v1/controls", headers=headers_a)
        assert response.status_code == status.HTTP_200_OK
        controls = response.json()
        control_ids = [c["id"] for c in controls]
        assert control_b_id not in control_ids


class TestControlsGetIsolation:
    """Test GET /api/v1/controls/{control_id} isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a, db_session
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        # Create a control first
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers_with_membership = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_a.id),
        }
        
        control_data = {
            "control_code": "AC-001",
            "name": "Test Control",
            "is_key": False,
            "is_automated": False,
        }
        response = client.post("/api/v1/controls", json=control_data, headers=headers_with_membership)
        control = response.json()
        control_id = control["id"]
        
        # Try to get control without membership header
        headers_no_membership = {"Authorization": f"Bearer {token}"}
        response = client.get(f"/api/v1/controls/{control_id}", headers=headers_no_membership)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_cross_tenant_read_by_id_blocked(
        self, client, tenant_a, tenant_b, user_tenant_a, user_tenant_b, db_session
    ):
        """User in Tenant A cannot access Tenant B's control by ID."""
        user_a, membership_a = user_tenant_a
        user_b, membership_b = user_tenant_b
        
        # User B creates a control in Tenant B
        token_b = create_dev_token(
            user_id=user_b.id,
            tenant_id=tenant_b.id,
            role=membership_b.role,
            is_platform_admin=False,
        )
        headers_b = {
            "Authorization": f"Bearer {token_b}",
            "X-Membership-Id": str(membership_b.id),
        }
        
        control_data = {
            "control_code": "AC-001",
            "name": "Tenant B Control",
            "is_key": False,
            "is_automated": False,
        }
        response = client.post("/api/v1/controls", json=control_data, headers=headers_b)
        control_b = response.json()
        control_b_id = control_b["id"]
        
        # User A tries to access Tenant B's control by ID
        token_a = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers_a = {
            "Authorization": f"Bearer {token_a}",
            "X-Membership-Id": str(membership_a.id),
        }
        
        response = client.get(f"/api/v1/controls/{control_b_id}", headers=headers_a)
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_nonexistent_control_returns_404(
        self, client, tenant_a, user_tenant_a
    ):
        """Non-existent control ID returns 404."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_a.id),
        }
        
        fake_id = uuid4()
        response = client.get(f"/api/v1/controls/{fake_id}", headers=headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestControlsCreateIsolation:
    """Test POST /api/v1/controls isolation."""
    
    @pytest.mark.asyncio
    async def test_missing_membership_header_returns_403(
        self, client, tenant_a, user_tenant_a
    ):
        """Missing X-Membership-Id header returns 403."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        control_data = {
            "control_code": "AC-001",
            "name": "Test Control",
            "is_key": False,
            "is_automated": False,
        }
        response = client.post("/api/v1/controls", json=control_data, headers=headers)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_tenant_id_ignored_from_payload(
        self, client, tenant_a, tenant_b, user_tenant_a, db_session
    ):
        """tenant_id in request payload is ignored; derived from membership context."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_a.id),
        }
        
        # Try to create control with tenant_id pointing to Tenant B (should be ignored)
        control_data = {
            "control_code": "AC-001",
            "name": "Test Control",
            "is_key": False,
            "is_automated": False,
            "tenant_id": str(tenant_b.id),  # Should be ignored
        }
        
        response = client.post("/api/v1/controls", json=control_data, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        control = response.json()
        # Control should belong to Tenant A (from membership), not Tenant B
        assert control["tenant_id"] == str(tenant_a.id)
        assert control["tenant_id"] != str(tenant_b.id)
    
    @pytest.mark.asyncio
    async def test_control_created_in_correct_tenant(
        self, client, tenant_a, user_tenant_a, db_session
    ):
        """Control is created in the tenant from membership context."""
        user_a, membership_a = user_tenant_a
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_a.id),
        }
        
        control_data = {
            "control_code": "AC-001",
            "name": "Test Control",
            "is_key": False,
            "is_automated": False,
        }
        response = client.post("/api/v1/controls", json=control_data, headers=headers)
        assert response.status_code == status.HTTP_200_OK
        
        control = response.json()
        assert control["tenant_id"] == str(tenant_a.id)
        assert control["created_by_membership_id"] == str(membership_a.id)
        
        # Verify it appears in list
        list_response = client.get("/api/v1/controls", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        controls = list_response.json()
        assert len(controls) == 1
        assert controls[0]["id"] == control["id"]


class TestControlsMultiMembershipSwitching:
    """Test multi-membership switching for Controls."""
    
    @pytest.mark.asyncio
    async def test_switching_membership_shows_different_controls(
        self, client, tenant_a, tenant_b, user_tenant_a, db_session
    ):
        """User with two memberships sees different controls when switching."""
        user_a, membership_a = user_tenant_a
        
        # Create second membership for user_a in tenant_b
        from models.user_tenant import UserTenant
        
        membership_b = UserTenant(
            id=uuid4(),
            user_id=user_a.id,
            tenant_id=tenant_b.id,
            role="admin",
            is_default=False,
        )
        db_session.add(membership_b)
        await db_session.commit()
        
        token = create_dev_token(
            user_id=user_a.id,
            tenant_id=tenant_a.id,
            role=membership_a.role,
            is_platform_admin=False,
        )
        
        # Create control in Tenant A
        headers_a = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_a.id),
        }
        control_data_a = {
            "control_code": "AC-001",
            "name": "Tenant A Control",
            "is_key": False,
            "is_automated": False,
        }
        response_a = client.post("/api/v1/controls", json=control_data_a, headers=headers_a)
        assert response_a.status_code == status.HTTP_200_OK
        control_a = response_a.json()
        control_a_id = control_a["id"]
        
        # Create control in Tenant B
        headers_b = {
            "Authorization": f"Bearer {token}",
            "X-Membership-Id": str(membership_b.id),
        }
        control_data_b = {
            "control_code": "AC-001",  # Same code, different tenant
            "name": "Tenant B Control",
            "is_key": False,
            "is_automated": False,
        }
        response_b = client.post("/api/v1/controls", json=control_data_b, headers=headers_b)
        assert response_b.status_code == status.HTTP_200_OK
        control_b = response_b.json()
        control_b_id = control_b["id"]
        
        # List controls with membership_a - should only see Tenant A control
        list_response_a = client.get("/api/v1/controls", headers=headers_a)
        assert list_response_a.status_code == status.HTTP_200_OK
        controls_a = list_response_a.json()
        control_ids_a = [c["id"] for c in controls_a]
        assert control_a_id in control_ids_a
        assert control_b_id not in control_ids_a
        
        # List controls with membership_b - should only see Tenant B control
        list_response_b = client.get("/api/v1/controls", headers=headers_b)
        assert list_response_b.status_code == status.HTTP_200_OK
        controls_b = list_response_b.json()
        control_ids_b = [c["id"] for c in controls_b]
        assert control_b_id in control_ids_b
        assert control_a_id not in control_ids_b
        
        # Verify cross-tenant access is blocked
        get_response = client.get(f"/api/v1/controls/{control_b_id}", headers=headers_a)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

