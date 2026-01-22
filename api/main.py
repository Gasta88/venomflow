"""
VenomFlow GraphQL API

FastAPI application with Strawberry GraphQL for querying venom peptide data.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import strawberry
from strawberry.fastapi import GraphQLRouter

from schema.queries import Query
from schema.mutations import Mutation
from shared.config.settings import settings

# Create Strawberry schema
schema = strawberry.Schema(query=Query, mutation=Mutation)

# Create GraphQL router
graphql_app = GraphQLRouter(schema)

# Create FastAPI app
app = FastAPI(
    title="VenomFlow API",
    description="GraphQL API for venom peptide data",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include GraphQL router
app.include_router(graphql_app, prefix="/graphql")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "VenomFlow API",
        "version": "1.0.0",
        "graphql": "/graphql"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
