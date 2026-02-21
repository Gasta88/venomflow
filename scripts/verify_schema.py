#!/usr/bin/env python3
"""
VenomFlow Schema Verification Script
Verifies PostgreSQL schema has been correctly applied
"""

import sys
import os
from typing import Dict, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from shared.config.settings import settings

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text: str):
    """Print section header"""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{YELLOW}⚠ {text}{RESET}")

def get_db_connection():
    """Create database connection from environment variables"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
        return conn
    except Exception as e:
        print_error(f"Failed to connect to database: {e}")
        sys.exit(1)

def verify_extensions(cursor) -> Tuple[bool, int]:
    """Verify required PostgreSQL extensions"""
    print_header("1. Verifying Extensions")
    
    cursor.execute("""
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname IN ('uuid-ossp', 'pg_trgm')
        ORDER BY extname
    """)
    
    extensions = cursor.fetchall()
    required_extensions = {'uuid-ossp', 'pg_trgm'}
    found_extensions = {ext['extname'] for ext in extensions}
    
    for ext in extensions:
        print_success(f"Extension '{ext['extname']}' version {ext['extversion']} installed")
    
    missing = required_extensions - found_extensions
    if missing:
        for ext in missing:
            print_error(f"Extension '{ext}' is missing")
        return False, len(extensions)
    
    return True, len(extensions)

def verify_tables(cursor) -> Tuple[bool, int]:
    """Verify all required tables exist"""
    print_header("2. Verifying Tables")
    
    required_tables = [
        'organisms',
        'peptides',
        'bioactivity',
        'structures',
        'properties',
        'peptide_similarities',
        'pipeline_runs',
        'screening_jobs'
    ]
    
    cursor.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename = ANY(%s)
        ORDER BY tablename
    """, (required_tables,))
    
    tables = cursor.fetchall()
    found_tables = {t['tablename'] for t in tables}
    
    for table in tables:
        print_success(f"Table '{table['tablename']}' exists")
    
    missing = set(required_tables) - found_tables
    if missing:
        for table in missing:
            print_error(f"Table '{table}' is missing")
        return False, len(tables)
    
    print(f"\nFound {len(tables)} tables (expected: 8)")
    return len(tables) == 8, len(tables)

def verify_indexes(cursor) -> Tuple[bool, int]:
    """Verify indexes are created"""
    print_header("3. Verifying Indexes")
    
    cursor.execute("""
        SELECT tablename, indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND indexname NOT LIKE '%_pkey'
        ORDER BY tablename, indexname
    """)
    
    indexes = cursor.fetchall()
    
    # Group by table
    table_indexes = {}
    for idx in indexes:
        table = idx['tablename']
        if table not in table_indexes:
            table_indexes[table] = []
        table_indexes[table].append(idx['indexname'])
    
    for table, idx_list in sorted(table_indexes.items()):
        print_success(f"Table '{table}': {len(idx_list)} indexes")
        for idx in idx_list:
            print(f"    - {idx}")
    
    total_indexes = len(indexes)
    print(f"\nTotal indexes: {total_indexes} (expected: 15+)")
    
    if total_indexes >= 15:
        print_success(f"Index count meets requirement ({total_indexes} >= 15)")
        return True, total_indexes
    else:
        print_warning(f"Index count below requirement ({total_indexes} < 15)")
        return False, total_indexes

def verify_foreign_keys(cursor) -> Tuple[bool, int]:
    """Verify foreign key constraints"""
    print_header("4. Verifying Foreign Key Constraints")
    
    cursor.execute("""
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            tc.constraint_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'public'
        ORDER BY tc.table_name, kcu.column_name
    """)
    
    foreign_keys = cursor.fetchall()
    
    for fk in foreign_keys:
        print_success(
            f"{fk['table_name']}.{fk['column_name']} -> "
            f"{fk['foreign_table_name']}.{fk['foreign_column_name']}"
        )
    
    print(f"\nTotal foreign keys: {len(foreign_keys)}")
    return True, len(foreign_keys)

def verify_triggers(cursor) -> Tuple[bool, int]:
    """Verify triggers are created"""
    print_header("5. Verifying Triggers")
    
    cursor.execute("""
        SELECT 
            event_object_table AS table_name,
            trigger_name,
            event_manipulation AS trigger_event
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
        AND trigger_name LIKE '%updated_at%'
        ORDER BY event_object_table
    """)
    
    triggers = cursor.fetchall()
    
    for trigger in triggers:
        print_success(
            f"Trigger '{trigger['trigger_name']}' on table '{trigger['table_name']}'"
        )
    
    expected_trigger_count = 6
    actual_count = len(triggers)
    print(f"\nTotal triggers: {actual_count} (expected: {expected_trigger_count})")
    
    if actual_count == expected_trigger_count:
        print_success(f"Trigger count matches requirement")
        return True, actual_count
    else:
        print_warning(f"Trigger count mismatch (expected {expected_trigger_count}, got {actual_count})")
        return False, actual_count

def verify_views(cursor) -> Tuple[bool, int]:
    """Verify views are created"""
    print_header("6. Verifying Views")
    
    cursor.execute("""
        SELECT table_name AS view_name
        FROM information_schema.views
        WHERE table_schema = 'public'
        AND table_name = 'peptides_enriched'
    """)
    
    views = cursor.fetchall()
    
    if views:
        for view in views:
            print_success(f"View '{view['view_name']}' exists")
            
        # Test if view is queryable
        try:
            cursor.execute("SELECT * FROM peptides_enriched LIMIT 0")
            print_success("View 'peptides_enriched' is queryable")
            return True, len(views)
        except Exception as e:
            print_error(f"View 'peptides_enriched' query failed: {e}")
            return False, len(views)
    else:
        print_error("View 'peptides_enriched' not found")
        return False, 0

def verify_functions(cursor) -> Tuple[bool, int]:
    """Verify functions are created"""
    print_header("7. Verifying Functions")
    
    cursor.execute("""
        SELECT 
            routine_name AS function_name,
            data_type AS return_type
        FROM information_schema.routines
        WHERE routine_schema = 'public'
        AND routine_name IN ('calculate_peptide_quality', 'update_updated_at_column')
        ORDER BY routine_name
    """)
    
    functions = cursor.fetchall()
    
    for func in functions:
        print_success(
            f"Function '{func['function_name']}' returns {func['return_type']}"
        )
    
    expected_functions = 2
    actual_count = len(functions)
    
    if actual_count == expected_functions:
        print_success(f"All required functions exist ({actual_count}/{expected_functions})")
        return True, actual_count
    else:
        print_error(f"Function count mismatch (expected {expected_functions}, got {actual_count})")
        return False, actual_count

def verify_table_columns(cursor):
    """Verify table column counts"""
    print_header("8. Verifying Table Columns")
    
    cursor.execute("""
        SELECT 
            table_name,
            COUNT(*) AS column_count
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name IN (
            'organisms',
            'peptides',
            'bioactivity',
            'structures',
            'properties',
            'peptide_similarities',
            'pipeline_runs',
            'screening_jobs'
        )
        GROUP BY table_name
        ORDER BY table_name
    """)
    
    tables = cursor.fetchall()
    
    for table in tables:
        print_success(f"Table '{table['table_name']}': {table['column_count']} columns")

def print_summary(results: Dict):
    """Print verification summary"""
    print_header("VERIFICATION SUMMARY")
    
    print("\nSuccess Criteria Checklist:")
    print(f"{'✓' if results['tables'][0] else '✗'} All 8 core tables exist ({results['tables'][1]}/8)")
    print(f"{'✓' if results['indexes'][0] else '✗'} 15+ indexes created ({results['indexes'][1]})")
    print(f"{'✓' if results['triggers'][0] else '✗'} 6 triggers active ({results['triggers'][1]}/6)")
    print(f"{'✓' if results['views'][0] else '✗'} peptides_enriched view queryable ({results['views'][1]}/1)")
    print(f"{'✓' if results['functions'][0] else '✗'} Functions executable ({results['functions'][1]}/2)")
    
    all_passed = all(result[0] for result in results.values())
    
    print("\n" + "=" * 80)
    if all_passed:
        print_success("✓ ALL VERIFICATION CHECKS PASSED!")
    else:
        print_error("✗ SOME VERIFICATION CHECKS FAILED")
        print_warning("Please review the issues above and reapply the schema if necessary")
    print("=" * 80 + "\n")
    
    return all_passed

def main():
    """Main verification function"""
    print_header("VenomFlow Database Schema Verification")
    
    # Connect to database
    print("Connecting to database...")
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print_success(f"Connected to database '{settings.postgres_db}'")
    
    # Run all verifications
    results = {}
    
    try:
        results['extensions'] = verify_extensions(cursor)
        results['tables'] = verify_tables(cursor)
        results['indexes'] = verify_indexes(cursor)
        results['foreign_keys'] = verify_foreign_keys(cursor)
        results['triggers'] = verify_triggers(cursor)
        results['views'] = verify_views(cursor)
        results['functions'] = verify_functions(cursor)
        verify_table_columns(cursor)
        
        # Print summary
        success = print_summary(results)
        
        # Cleanup
        cursor.close()
        conn.close()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print_error(f"Verification failed with error: {e}")
        cursor.close()
        conn.close()
        sys.exit(1)

if __name__ == "__main__":
    main()
