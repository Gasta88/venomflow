#!/usr/bin/env python3
"""
VenomFlow Schema Static Analysis
Analyzes the schema.sql file without requiring a database connection
"""

import re
from pathlib import Path
from typing import Dict

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

def print_info(text: str):
    """Print info message"""
    print(f"  {text}")

def analyze_schema(schema_path: Path) -> Dict:
    """Analyze the schema.sql file"""
    
    with open(schema_path, 'r') as f:
        content = f.read()
    
    results = {
        'extensions': [],
        'tables': [],
        'indexes': [],
        'triggers': [],
        'views': [],
        'functions': [],
        'foreign_keys': []
    }
    
    # Find extensions
    extension_pattern = r'CREATE EXTENSION IF NOT EXISTS\s+"([^"]+)"'
    results['extensions'] = re.findall(extension_pattern, content, re.IGNORECASE)
    
    # Find tables
    table_pattern = r'CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\('
    results['tables'] = re.findall(table_pattern, content, re.IGNORECASE)
    
    # Find indexes
    index_pattern = r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)'
    results['indexes'] = re.findall(index_pattern, content, re.IGNORECASE)
    
    # Find triggers
    trigger_pattern = r'CREATE TRIGGER\s+(\w+)'
    results['triggers'] = re.findall(trigger_pattern, content, re.IGNORECASE)
    
    # Find views
    view_pattern = r'CREATE\s+(?:OR REPLACE\s+)?VIEW\s+(\w+)'
    results['views'] = re.findall(view_pattern, content, re.IGNORECASE)
    
    # Find functions
    function_pattern = r'CREATE\s+(?:OR REPLACE\s+)?FUNCTION\s+(\w+)'
    results['functions'] = re.findall(function_pattern, content, re.IGNORECASE)
    
    # Find foreign keys
    fk_pattern = r'REFERENCES\s+(\w+)\s*\((\w+)\)'
    results['foreign_keys'] = re.findall(fk_pattern, content, re.IGNORECASE)
    
    return results

def verify_requirements(results: Dict) -> bool:
    """Verify that requirements are met"""
    
    print_header("VenomFlow Schema Static Analysis Results")
    
    # Expected values
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
    
    expected_extensions = ['uuid-ossp', 'pg_trgm']
    
    all_passed = True
    
    # Check extensions
    print_header("1. Extensions")
    for ext in results['extensions']:
        print_success(f"Extension: {ext}")
    
    if set(expected_extensions) == set(results['extensions']):
        print_success(f"All required extensions found ({len(results['extensions'])}/2)")
    else:
        print_error(f"Extension mismatch")
        all_passed = False
    
    # Check tables
    print_header("2. Tables")
    found_tables = [t.lower() for t in results['tables']]
    for table in found_tables:
        print_success(f"Table: {table}")
    
    if set(expected_tables) == set(found_tables):
        print_success(f"All 8 core tables found ({len(found_tables)}/8)")
    else:
        print_error(f"Table count mismatch")
        missing = set(expected_tables) - set(found_tables)
        if missing:
            print_error(f"Missing tables: {missing}")
        all_passed = False
    
    # Check indexes
    print_header("3. Indexes")
    print_info(f"Total indexes defined: {len(results['indexes'])}")
    
    # Group indexes by table prefix
    table_indexes = {}
    for idx in results['indexes']:
        # Extract table name from index name (idx_tablename_...)
        parts = idx.split('_')
        if len(parts) >= 2:
            table = parts[1]
            if table not in table_indexes:
                table_indexes[table] = []
            table_indexes[table].append(idx)
    
    for table, indexes in sorted(table_indexes.items()):
        print_info(f"  {table}: {len(indexes)} indexes")
    
    if len(results['indexes']) >= 15:
        print_success(f"Index requirement met ({len(results['indexes'])} >= 15)")
    else:
        print_error(f"Index count below requirement ({len(results['indexes'])} < 15)")
        all_passed = False
    
    # Check triggers
    print_header("4. Triggers")
    for trigger in results['triggers']:
        print_success(f"Trigger: {trigger}")
    
    expected_trigger_count = 6  # One for each table with updated_at
    if len(results['triggers']) >= expected_trigger_count:
        print_success(f"Trigger requirement met ({len(results['triggers'])}/{expected_trigger_count})")
    else:
        print_error(f"Trigger count below requirement ({len(results['triggers'])} < {expected_trigger_count})")
        all_passed = False
    
    # Check views
    print_header("5. Views")
    for view in results['views']:
        print_success(f"View: {view}")
    
    if 'peptides_enriched' in [v.lower() for v in results['views']]:
        print_success("peptides_enriched view found")
    else:
        print_error("peptides_enriched view not found")
        all_passed = False
    
    # Check functions
    print_header("6. Functions")
    for func in results['functions']:
        print_success(f"Function: {func}")
    
    expected_functions = ['calculate_peptide_quality', 'update_updated_at_column']
    found_functions = [f.lower() for f in results['functions']]
    
    if set(expected_functions) <= set(found_functions):
        print_success(f"All required functions found ({len(results['functions'])}/2)")
    else:
        print_error("Some required functions missing")
        missing = set(expected_functions) - set(found_functions)
        if missing:
            print_error(f"Missing functions: {missing}")
        all_passed = False
    
    # Check foreign keys
    print_header("7. Foreign Key Constraints")
    print_info(f"Total foreign key references: {len(results['foreign_keys'])}")
    
    # Group by referenced table
    fk_by_table = {}
    for table, column in results['foreign_keys']:
        if table not in fk_by_table:
            fk_by_table[table] = []
        fk_by_table[table].append(column)
    
    for table, columns in sorted(fk_by_table.items()):
        print_info(f"  → {table}: {len(columns)} references")
    
    if len(results['foreign_keys']) > 0:
        print_success("Foreign key constraints defined")
    else:
        print_error("No foreign key constraints found")
        all_passed = False
    
    # Summary
    print_header("SUCCESS CRITERIA VERIFICATION")
    
    criteria = [
        ("All 8 tables defined", len(found_tables) == 8),
        ("15+ indexes created", len(results['indexes']) >= 15),
        ("6 triggers for updated_at", len(results['triggers']) >= 6),
        ("peptides_enriched view", 'peptides_enriched' in [v.lower() for v in results['views']]),
        ("calculate_peptide_quality() function", 'calculate_peptide_quality' in found_functions),
        ("Foreign keys enforce integrity", len(results['foreign_keys']) > 0),
    ]
    
    for criterion, passed in criteria:
        if passed:
            print_success(criterion)
        else:
            print_error(criterion)
    
    # Final summary
    print_header("OVERALL RESULT")
    
    if all_passed:
        print_success("✓ ALL CRITERIA MET - Schema is complete!")
        print_success("✓ Ready for database deployment")
    else:
        print_error("✗ SOME CRITERIA NOT MET - Please review the schema")
    
    print()
    
    return all_passed

def main():
    """Main function"""
    # Find schema file
    schema_path = Path(__file__).parent.parent / 'shared' / 'database' / 'schema.sql'
    
    if not schema_path.exists():
        print_error(f"Schema file not found: {schema_path}")
        return 1
    
    print_header("VenomFlow Schema Static Analysis")
    print_info(f"Analyzing: {schema_path}")
    
    # Analyze schema
    results = analyze_schema(schema_path)
    
    # Verify requirements
    success = verify_requirements(results)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
