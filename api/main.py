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
from prometheus_fastapi_instrumentator import Instrumentator
from strawberry.fastapi import GraphQLRouter

from schema.queries import Query

# =============================================================================
# GRAPHQL SCHEMA DEFINITION
# =============================================================================

# Create Strawberry schema with Query resolvers
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
        "http://localhost:3000",  # Frontend / Dagster UI
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
# PROMETHEUS METRICS INSTRUMENTATION
# =============================================================================

# Expose Prometheus metrics at /metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["Monitoring"])

# =============================================================================
# APPLICATION STARTUP
# =============================================================================


@app.on_event("startup")
async def startup_event() -> None:
    """Execute on application startup"""
    print("VenomFlow API starting...")
    print("GraphQL Playground available at: http://localhost:8000/graphql")
    print("Health check available at: http://localhost:8000/health")
    print("Prometheus metrics available at: http://localhost:8000/metrics")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Execute on application shutdown"""
    print("VenomFlow API shutting down...")


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
