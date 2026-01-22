"""
GraphQL Mutation definitions for VenomFlow API
"""

import strawberry
from typing import Optional


@strawberry.type
class MutationResponse:
    """Generic mutation response."""
    success: bool
    message: str
    id: Optional[str] = None


@strawberry.type
class Mutation:
    """Root Mutation type."""
    
    @strawberry.mutation
    def trigger_pipeline(self, pipeline_name: str) -> MutationResponse:
        """Trigger a Dagster pipeline run."""
        # TODO: Implement pipeline triggering via Dagster API
        return MutationResponse(
            success=False,
            message="Pipeline triggering not yet implemented"
        )
    
    @strawberry.mutation
    def update_peptide_annotation(
        self, 
        peptide_id: str, 
        annotation: str
    ) -> MutationResponse:
        """Update peptide annotation."""
        # TODO: Implement annotation update
        return MutationResponse(
            success=False,
            message="Annotation update not yet implemented"
        )
