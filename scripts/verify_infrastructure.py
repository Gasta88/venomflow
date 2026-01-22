#!/usr/bin/env python3
"""
Verify VenomFlow infrastructure

Checks that all services are running and accessible.
"""

import sys
import requests
import psycopg2
import redis
import os
from time import sleep


def check_postgres():
    """Check PostgreSQL connection."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "venomflow"),
            user=os.getenv("POSTGRES_USER", "venomflow_user"),
            password=os.getenv("POSTGRES_PASSWORD", "password")
        )
        conn.close()
        print("✓ PostgreSQL is accessible")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL error: {e}")
        return False


def check_redis():
    """Check Redis connection."""
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        r.ping()
        print("✓ Redis is accessible")
        return True
    except Exception as e:
        print(f"✗ Redis error: {e}")
        return False


def check_api():
    """Check API availability."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✓ API is accessible")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ API error: {e}")
        return False


def check_dagster():
    """Check Dagster webserver."""
    try:
        response = requests.get("http://localhost:3001", timeout=5)
        if response.status_code == 200:
            print("✓ Dagster webserver is accessible")
            return True
        else:
            print(f"✗ Dagster returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Dagster error: {e}")
        return False


def main():
    """Run all infrastructure checks."""
    print("Verifying VenomFlow infrastructure...\n")
    
    checks = [
        check_postgres(),
        check_redis(),
        check_api(),
        check_dagster(),
    ]
    
    print(f"\nResults: {sum(checks)}/{len(checks)} checks passed")
    
    if all(checks):
        print("\n✓ All infrastructure components are operational!")
        return 0
    else:
        print("\n✗ Some infrastructure components are not available")
        return 1


if __name__ == "__main__":
    sys.exit(main())
