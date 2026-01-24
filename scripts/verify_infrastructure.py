#!/usr/bin/env python3
"""
Infrastructure Verification Script for VenomFlow
Tests connectivity and health of all Docker services.
"""
import os
import sys
import time
import psycopg2
import redis
import requests
from minio import Minio
from elasticsearch import Elasticsearch
from typing import Tuple

# Load environment variables
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.config.settings import settings


def test_postgres() -> Tuple[bool, str]:
    """Test PostgreSQL connectivity."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db,
            connect_timeout=settings.postgres_pool_timeout
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return True, f"PostgreSQL connected ({version.split(',')[0]})"
    except Exception as e:
        return False, f"PostgreSQL connection failed: {str(e)}"


def test_redis() -> Tuple[bool, str]:
    """Test Redis connectivity."""
    try:
        client = redis.Redis(
            host="localhost",
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            socket_timeout=settings.redis_socket_timeout
        )
        pong = client.ping()
        info = client.info('server')
        version = info['redis_version']
        client.close()
        return True, f"Redis connected (v{version})"
    except Exception as e:
        return False, f"Redis connection failed: {str(e)}"


def test_elasticsearch() -> Tuple[bool, str]:
    """Test Elasticsearch connectivity."""
    try:
        es = Elasticsearch(
            [f"{settings.elastic_scheme}://{settings.elastic_user}:{settings.elastic_password}@localhost:{settings.elastic_port}"],
            basic_auth=(settings.elastic_user, settings.elastic_password),
            verify_certs=False,
            request_timeout=10
        )
        try: 
            es.ping()
            info = es.info()
            version = info['version']['number']
            cluster = info['cluster_name']
            return True, f"Elasticsearch connected (v{version}, cluster: {cluster})"
        except Exception as e:
            return False, f"Elasticsearch ping failed: {str(e)}"
    except Exception as e:
        return False, f"Elasticsearch connection failed: {str(e)}"


def test_minio() -> Tuple[bool, str]:
    """Test MinIO connectivity."""
    try:
        client = Minio(
            f"localhost:{settings.minio_port}",
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        # List buckets to verify connectivity
        buckets = client.list_buckets()
        return True, f"MinIO connected ({len(buckets)} buckets)"
    except Exception as e:
        return False, f"MinIO connection failed: {str(e)}"


def test_prometheus() -> Tuple[bool, str]:
    """Test Prometheus connectivity."""
    try:
        url = f"http://localhost:{os.getenv('PROMETHEUS_PORT', '9090')}/api/v1/status/config"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return True, "Prometheus API responding"
        else:
            return False, f"Prometheus returned status {response.status_code}"
    except Exception as e:
        return False, f"Prometheus connection failed: {str(e)}"


def test_grafana() -> Tuple[bool, str]:
    """Test Grafana connectivity."""
    try:
        port = os.getenv('GRAFANA_PORT', '3001')
        url = f"http://localhost:{port}/api/health"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, f"Grafana {data.get('version', 'unknown')} running"
        else:
            return False, f"Grafana returned status {response.status_code}"
    except Exception as e:
        return False, f"Grafana connection failed: {str(e)}"


def main():
    """Run all infrastructure tests."""
    print("🔍 VenomFlow Infrastructure Verification\n")
    print("=" * 60)
    
    tests = [
        ("PostgreSQL", test_postgres),
        ("Redis", test_redis),
        ("Elasticsearch", test_elasticsearch),
        ("MinIO", test_minio),
        ("Prometheus", test_prometheus),
        ("Grafana", test_grafana),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n🧪 Testing {name}...", end=" ")
        success, message = test_func()
        results.append(success)
        
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"\n🎉 All {total} services verified successfully!")
        print("✅ Infrastructure is ready for development.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {passed}/{total} services verified.")
        print("❌ Please fix failing services before continuing.")
        print("\n💡 Troubleshooting tips:")
        print("  - Run: docker-compose ps")
        print("  - Check logs: docker-compose logs <service>")
        print("  - Verify .env file has correct credentials")
        print("  - Ensure Docker has enough memory (4GB+)")
        sys.exit(1)


if __name__ == "__main__":
    # Wait for services to fully start
    print("⏳ Waiting 10 seconds for services to initialize...")
    time.sleep(10)
    main()