#!/usr/bin/env python3
"""
VenomFlow Database Testing Script

Tests database schema, CRUD operations, views, and functions.
Validates that the database is properly initialized and ready for use.

Usage:
    python3 scripts/test_database.py

Exit Codes:
    0 - All tests passed
    1 - One or more tests failed
"""

import sys
import os
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlalchemy import text
    from shared.database.connection import engine, get_db_context, test_connection
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure SQLAlchemy is installed: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)


class DatabaseTester:
    """Database testing utility"""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def run_test(self, test_name: str, test_func):
        """Run a single test and track results"""
        try:
            print(f"\n🧪 {test_name}...", end=" ", flush=True)
            result = test_func()
            if result:
                print(f"✅ {result}")
                self.tests_passed += 1
                self.test_results.append((test_name, True, result))
            else:
                print(f"❌ Test returned False")
                self.tests_failed += 1
                self.test_results.append((test_name, False, "Test returned False"))
        except Exception as e:
            print(f"❌ {str(e)}")
            self.tests_failed += 1
            self.test_results.append((test_name, False, str(e)))
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        total_tests = self.tests_passed + self.tests_failed
        
        if self.tests_failed == 0:
            print(f"🎉 All {self.tests_passed} tests passed!")
        else:
            print(f"⚠️  {self.tests_passed}/{total_tests} tests passed")
            print(f"❌ {self.tests_failed} tests failed")
        
        print("=" * 60)
        
        return self.tests_failed == 0


def test_database_connection():
    """Test 1: Database connection"""
    if test_connection():
        return "Database connection test passed"
    else:
        raise Exception("Failed to connect to database")


def test_tables_exist():
    """Test 2: Verify all required tables exist"""
    expected_tables = [
        'organisms',
        'peptides',
        'bioactivity',
        'structures',
        'properties',
        'peptide_similarities',
        'pipeline_runs',
        'screening_jobs'
    ]
    
    with get_db_context() as db:
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        
        existing_tables = [row[0] for row in result]
        
        missing_tables = set(expected_tables) - set(existing_tables)
        if missing_tables:
            raise Exception(f"Missing tables: {missing_tables}")
        
        return f"All {len(expected_tables)} tables exist"


def test_crud_operations():
    """Test 3: Test basic CRUD operations"""
    
    with get_db_context() as db:
        # Create: Insert a test organism
        organism_id = uuid4()
        db.execute(text("""
            INSERT INTO organisms (id, name, common_name, taxonomy_id, venom_type, source)
            VALUES (:id, :name, :common_name, :taxonomy_id, :venom_type, :source)
        """), {
            "id": str(organism_id),
            "name": "Test Species",
            "common_name": "Test Snake",
            "taxonomy_id": 99999,
            "venom_type": "snake",
            "source": "manual"
        })
        
        # Read: Verify insertion
        result = db.execute(text("""
            SELECT name, common_name FROM organisms WHERE id = :id
        """), {"id": str(organism_id)})
        
        row = result.fetchone()
        if not row or row[0] != "Test Species":
            raise Exception("Failed to read inserted organism")
        
        # Update: Modify the organism
        db.execute(text("""
            UPDATE organisms 
            SET common_name = :new_name 
            WHERE id = :id
        """), {
            "new_name": "Updated Test Snake",
            "id": str(organism_id)
        })
        
        # Verify update
        result = db.execute(text("""
            SELECT common_name FROM organisms WHERE id = :id
        """), {"id": str(organism_id)})
        
        row = result.fetchone()
        if not row or row[0] != "Updated Test Snake":
            raise Exception("Failed to update organism")
        
        # Delete: Remove test data
        db.execute(text("""
            DELETE FROM organisms WHERE id = :id
        """), {"id": str(organism_id)})
        
        # Verify deletion
        result = db.execute(text("""
            SELECT COUNT(*) FROM organisms WHERE id = :id
        """), {"id": str(organism_id)})
        
        count = result.fetchone()[0]
        if count != 0:
            raise Exception("Failed to delete organism")
        
        db.commit()
    
    return "CRUD operations work correctly"


def test_view_peptides_enriched():
    """Test 4: Test peptides_enriched view"""
    
    with get_db_context() as db:
        # Check if view exists
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.views 
            WHERE table_schema = 'public' 
            AND table_name = 'peptides_enriched'
        """))
        
        view_count = result.fetchone()[0]
        if view_count == 0:
            raise Exception("View 'peptides_enriched' does not exist")
        
        # Test if view is queryable
        result = db.execute(text("""
            SELECT COUNT(*) FROM peptides_enriched
        """))
        
        # Should execute without error (even if count is 0)
        count = result.fetchone()[0]
        
        return f"View 'peptides_enriched' is queryable (contains {count} records)"


def test_function_calculate_quality():
    """Test 5: Test calculate_peptide_quality function"""
    
    with get_db_context() as db:
        # Create test data
        organism_id = uuid4()
        peptide_id = uuid4()
        
        # Insert organism
        db.execute(text("""
            INSERT INTO organisms (id, name, venom_type, source)
            VALUES (:id, :name, :venom_type, :source)
        """), {
            "id": str(organism_id),
            "name": "Test Organism",
            "venom_type": "snake",
            "source": "manual"
        })
        
        # Insert peptide
        db.execute(text("""
            INSERT INTO peptides (id, name, sequence, sequence_hash, sequence_length, 
                                  organism_id, source)
            VALUES (:id, :name, :sequence, :hash, :length, :organism_id, :source)
        """), {
            "id": str(peptide_id),
            "name": "Test Peptide",
            "sequence": "ACDEFGHIKLMNPQRSTVWY",
            "hash": "test_hash_12345",
            "length": 20,
            "organism_id": str(organism_id),
            "source": "manual"
        })
        
        db.commit()
        
        # Test the function
        result = db.execute(text("""
            SELECT calculate_peptide_quality(:peptide_id)
        """), {"peptide_id": str(peptide_id)})
        
        quality_score = result.fetchone()[0]
        
        # Clean up
        db.execute(text("DELETE FROM peptides WHERE id = :id"), {"id": str(peptide_id)})
        db.execute(text("DELETE FROM organisms WHERE id = :id"), {"id": str(organism_id)})
        db.commit()
        
        if quality_score is None:
            raise Exception("Function returned NULL")
        
        if not (0.0 <= float(quality_score) <= 1.0):
            raise Exception(f"Quality score out of range: {quality_score}")
        
        return f"Function 'calculate_peptide_quality()' works (score: {quality_score})"


def test_triggers():
    """Test 6: Test updated_at triggers"""
    
    with get_db_context() as db:
        # Create test organism
        organism_id = uuid4()
        
        db.execute(text("""
            INSERT INTO organisms (id, name, venom_type, source, created_at, updated_at)
            VALUES (:id, :name, :venom_type, :source, :created, :updated)
        """), {
            "id": str(organism_id),
            "name": "Trigger Test",
            "venom_type": "snake",
            "source": "manual",
            "created": datetime.now(),
            "updated": datetime.now()
        })
        
        db.commit()
        
        # Get initial updated_at
        result = db.execute(text("""
            SELECT updated_at FROM organisms WHERE id = :id
        """), {"id": str(organism_id)})
        
        initial_updated = result.fetchone()[0]
        
        # Wait a moment and update
        import time
        time.sleep(0.1)
        
        db.execute(text("""
            UPDATE organisms SET name = :name WHERE id = :id
        """), {
            "name": "Trigger Test Updated",
            "id": str(organism_id)
        })
        
        db.commit()
        
        # Get new updated_at
        result = db.execute(text("""
            SELECT updated_at FROM organisms WHERE id = :id
        """), {"id": str(organism_id)})
        
        new_updated = result.fetchone()[0]
        
        # Clean up
        db.execute(text("DELETE FROM organisms WHERE id = :id"), {"id": str(organism_id)})
        db.commit()
        
        if new_updated <= initial_updated:
            raise Exception("Trigger did not update updated_at timestamp")
        
        return "Triggers automatically update updated_at timestamps"


def test_indexes():
    """Test 7: Verify indexes exist"""
    
    with get_db_context() as db:
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM pg_indexes 
            WHERE schemaname = 'public'
            AND indexname NOT LIKE '%_pkey'
        """))
        
        index_count = result.fetchone()[0]
        
        if index_count < 15:
            raise Exception(f"Expected at least 15 indexes, found {index_count}")
        
        return f"Found {index_count} indexes (requirement: 15+)"


def test_foreign_keys():
    """Test 8: Verify foreign key constraints"""
    
    with get_db_context() as db:
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.table_constraints 
            WHERE constraint_type = 'FOREIGN KEY'
            AND table_schema = 'public'
        """))
        
        fk_count = result.fetchone()[0]
        
        if fk_count == 0:
            raise Exception("No foreign key constraints found")
        
        return f"Found {fk_count} foreign key constraints"


def main():
    """Main test runner"""
    
    print("")
    print("🧪 Testing VenomFlow Database Schema")
    print("=" * 60)
    
    tester = DatabaseTester()
    
    # Run all tests
    tester.run_test("Database Connection", test_database_connection)
    tester.run_test("Tables Exist", test_tables_exist)
    tester.run_test("CRUD Operations", test_crud_operations)
    tester.run_test("View (peptides_enriched)", test_view_peptides_enriched)
    tester.run_test("Function (calculate_peptide_quality)", test_function_calculate_quality)
    tester.run_test("Triggers (updated_at)", test_triggers)
    tester.run_test("Indexes", test_indexes)
    tester.run_test("Foreign Keys", test_foreign_keys)
    
    # Print summary and exit
    success = tester.print_summary()
    
    print("")
    
    if success:
        print("✅ Database is ready for development!")
        print("")
        sys.exit(0)
    else:
        print("❌ Database has issues that need to be fixed")
        print("")
        sys.exit(1)


if __name__ == "__main__":
    main()
