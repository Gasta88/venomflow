"""
VenomFlow FastAPI Application with Strawberry GraphQL Integration

This module provides:
- FastAPI HTTP server with async support
- Strawberry GraphQL endpoint at /graphql
- CORS middleware for frontend access
- Health check endpoint for monitoring
- GraphQL Playground for interactive API exploration
"""

from typing import Any, Dict

import strawberry
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

# =============================================================================
# GRAPHQL SCHEMA DEFINITION
# =============================================================================


@strawberry.type
class Query:
    """Root Query type for GraphQL schema"""

    @strawberry.field
    def health(self) -> str:
        """Health check query for GraphQL endpoint"""
        return "GraphQL is healthy!"

    @strawberry.field
    def hello(self, name: str = "World") -> str:
        """Simple hello query for testing"""
        return f"Hello, {name}!"


# Create Strawberry schema
schema = strawberry.Schema(query=Query)

# =============================================================================
# FASTAPI APPLICATION SETUP
# =============================================================================

# Initialize FastAPI application
app = FastAPI(
    title="VenomFlow API",
    description="GraphQL API for comprehensive venom peptide research",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# CORS MIDDLEWARE CONFIGURATION
# =============================================================================

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Dagster UI
        "http://localhost:3001",  # Grafana
        "http://localhost:8000",  # API itself
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# HEALTH CHECK ENDPOINT
# =============================================================================


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for monitoring and load balancers
    
    Returns:
        Dict with status indicator
    """
    return {"status": "healthy"}


# =============================================================================
# GRAPHQL ENDPOINT
# =============================================================================

# Create GraphQL router with Playground enabled
graphql_app = GraphQLRouter(
    schema,
    graphiql=True,  # Enable GraphQL Playground
)

# Mount GraphQL endpoint
app.include_router(graphql_app, prefix="/graphql")

# =============================================================================
# APPLICATION STARTUP
# =============================================================================


@app.on_event("startup")
async def startup_event() -> None:
    """Execute on application startup"""
    print("🚀 VenomFlow API starting...")
    print("📊 GraphQL Playground available at: http://localhost:8000/graphql")
    print("❤️  Health check available at: http://localhost:8000/health")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Execute on application shutdown"""
    print("👋 VenomFlow API shutting down...")


# =============================================================================
# ROOT ENDPOINT
# =============================================================================


@app.get("/", tags=["Root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint with API information
    
    Returns:
        Dict with API details and available endpoints
    """
    return {
        "name": "VenomFlow API",
        "version": "1.0.0",
        "description": "GraphQL API for venom peptide research",
        "endpoints": {
            "health": "/health",
            "graphql": "/graphql",
            "docs": "/docs",
            "redoc": "/redoc",
        },
    }
