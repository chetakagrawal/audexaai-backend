"""Service to resolve project line items (Control × Application × Test Attribute) with effective values."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.tenancy import TenancyContext
from models.project_control import ProjectControl
from models.project_control_application import ProjectControlApplication
from models.test_attribute import TestAttribute
from models.control import Control
from models.application import Application
from repos import (
    project_controls_repo,
    project_control_applications_repo,
    test_attributes_repo,
    project_test_attribute_overrides_repo,
)


class ResolvedLineItem:
    """DTO for a resolved line item with effective values."""

    def __init__(
        self,
        project_control_id: UUID,
        control_id: UUID,
        control_code: str,
        control_name: str,
        application_id: UUID,
        application_name: str,
        test_attribute_id: UUID,
        test_attribute_code: str,
        test_attribute_name: str,
        pinned_control_version_num: int,
        pinned_test_attribute_version_num: int,
        effective_procedure: str | None,
        effective_evidence: str | None,
        source: str,  # 'base' | 'project_global_override' | 'project_app_override'
        override_id: UUID | None,
    ):
        self.project_control_id = project_control_id
        self.control_id = control_id
        self.control_code = control_code
        self.control_name = control_name
        self.application_id = application_id
        self.application_name = application_name
        self.test_attribute_id = test_attribute_id
        self.test_attribute_code = test_attribute_code
        self.test_attribute_name = test_attribute_name
        self.pinned_control_version_num = pinned_control_version_num
        self.pinned_test_attribute_version_num = pinned_test_attribute_version_num
        self.effective_procedure = effective_procedure
        self.effective_evidence = effective_evidence
        self.source = source
        self.override_id = override_id


async def resolve_line_items(
    session: AsyncSession,
    *,
    membership_ctx: TenancyContext,
    project_id: UUID,
    control_id: UUID | None = None,
) -> list[ResolvedLineItem]:
    """
    Resolve all line items for a project with effective procedure/evidence.
    
    Line items are: ProjectControl × Application (via ProjectControlApplication) × TestAttribute
    
    For each line item, computes effective procedure and evidence using precedence:
    1. App-specific project override (if exists)
    2. Global project override (if exists)
    3. Base test attribute
    
    Args:
        session: Database session
        membership_ctx: Tenancy context
        project_id: Project ID
        control_id: Optional control ID to filter by
    
    Returns:
        List of ResolvedLineItem DTOs
    
    Raises:
        HTTPException: 404 if project not found
    """
    tenant_id = membership_ctx.tenant_id

    # Get all active project controls for the project
    project_controls = await project_controls_repo.list_by_project(
        session,
        tenant_id=tenant_id,
        project_id=project_id,
        include_removed=False,
    )

    if control_id:
        project_controls = [pc for pc in project_controls if pc.control_id == control_id]

    if not project_controls:
        return []

    # Load controls and test attributes in bulk
    control_ids = {pc.control_id for pc in project_controls}
    controls_query = select(Control).where(
        Control.tenant_id == tenant_id,
        Control.id.in_(control_ids),
        Control.deleted_at.is_(None),
    )
    controls_result = await session.execute(controls_query)
    controls_dict = {c.id: c for c in controls_result.scalars().all()}

    # Get all test attributes for these controls
    test_attrs_query = select(TestAttribute).where(
        TestAttribute.tenant_id == tenant_id,
        TestAttribute.control_id.in_(control_ids),
        TestAttribute.deleted_at.is_(None),
    )
    test_attrs_result = await session.execute(test_attrs_query)
    test_attrs_by_control = {}
    for ta in test_attrs_result.scalars().all():
        if ta.control_id not in test_attrs_by_control:
            test_attrs_by_control[ta.control_id] = []
        test_attrs_by_control[ta.control_id].append(ta)

    # Get all active applications for these project controls
    project_control_ids = {pc.id for pc in project_controls}
    pca_list = []
    for pc_id in project_control_ids:
        pcas = await project_control_applications_repo.list_active_by_project_control(
            session,
            tenant_id=tenant_id,
            project_control_id=pc_id,
        )
        pca_list.extend(pcas)

    # Load applications in bulk
    application_ids = {pca.application_id for pca in pca_list}
    applications_query = select(Application).where(
        Application.tenant_id == tenant_id,
        Application.id.in_(application_ids),
        Application.deleted_at.is_(None),
    )
    applications_result = await session.execute(applications_query)
    applications_dict = {a.id: a for a in applications_result.scalars().all()}

    # Build line items
    resolved_items = []

    for project_control in project_controls:
        control = controls_dict.get(project_control.control_id)
        if not control:
            continue

        # Get test attributes for this control
        test_attributes = test_attrs_by_control.get(project_control.control_id, [])

        # Get applications for this project control
        project_control_apps = [
            pca for pca in pca_list if pca.project_control_id == project_control.id
        ]

        # For each (application, test_attribute) combination
        for pca in project_control_apps:
            application = applications_dict.get(pca.application_id)
            if not application:
                continue

            for test_attribute in test_attributes:
                # Resolve effective values with precedence
                override = None
                source = "base"

                # Try app-specific override first
                override = await project_test_attribute_overrides_repo.get_active_app(
                    session,
                    tenant_id=tenant_id,
                    project_control_id=project_control.id,
                    application_id=pca.application_id,
                    test_attribute_id=test_attribute.id,
                )
                if override:
                    source = "project_app_override"

                # If no app-specific, try global override
                if override is None:
                    override = await project_test_attribute_overrides_repo.get_active_global(
                        session,
                        tenant_id=tenant_id,
                        project_control_id=project_control.id,
                        test_attribute_id=test_attribute.id,
                    )
                    if override:
                        source = "project_global_override"

                # Compute effective values
                if override:
                    effective_procedure = (
                        override.procedure_override or test_attribute.test_procedure
                    )
                    effective_evidence = (
                        override.expected_evidence_override or test_attribute.expected_evidence
                    )
                    pinned_test_attribute_version_num = override.base_test_attribute_version_num
                    override_id = override.id
                else:
                    effective_procedure = test_attribute.test_procedure
                    effective_evidence = test_attribute.expected_evidence
                    pinned_test_attribute_version_num = test_attribute.row_version
                    override_id = None

                resolved_item = ResolvedLineItem(
                    project_control_id=project_control.id,
                    control_id=control.id,
                    control_code=control.control_code,
                    control_name=control.name,
                    application_id=application.id,
                    application_name=application.name,
                    test_attribute_id=test_attribute.id,
                    test_attribute_code=test_attribute.code,
                    test_attribute_name=test_attribute.name,
                    pinned_control_version_num=project_control.control_version_num,
                    pinned_test_attribute_version_num=pinned_test_attribute_version_num,
                    effective_procedure=effective_procedure,
                    effective_evidence=effective_evidence,
                    source=source,
                    override_id=override_id,
                )
                resolved_items.append(resolved_item)

    return resolved_items

