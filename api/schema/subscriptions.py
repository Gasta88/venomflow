"""
GraphQL Subscription definitions for VenomFlow API
"""

import strawberry
from typing import AsyncGenerator


@strawberry.type
class PipelineStatus:
    """Pipeline status update."""
    pipeline_name: str
    status: str
    progress: float


@strawberry.type
class Subscription:
    """Root Subscription type."""
    
    @strawberry.subscription
    async def pipeline_updates(self, pipeline_name: str) -> AsyncGenerator[PipelineStatus, None]:
        """Subscribe to pipeline status updates."""
        # TODO: Implement real-time pipeline status updates
        yield PipelineStatus(
            pipeline_name=pipeline_name,
            status="running",
            progress=0.5
        )
