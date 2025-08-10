#!/usr/bin/env python3
"""
Database initialization script for Court Case Fetcher
Creates the SQLite database and required tables
"""

import sqlite3
import os

def init_database():
    """Initialize the SQLite database with required tables"""
    
    # Remove existing database if it exists
    if os.path.exists('court_cases.db'):
        os.remove('court_cases.db')
        print("Removed existing database")
    
    # Create new database
    conn = sqlite3.connect('court_cases.db')
    cursor = conn.cursor()
    
    print("Creating database tables...")
    
    # Create searches table - matching app.py expectations
    cursor.execute('''
        CREATE TABLE searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT NOT NULL,
            case_type TEXT NOT NULL,
            filing_year INTEGER NOT NULL,
            search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_message TEXT
        )
    ''')
    print("✓ Created 'searches' table")
    
    # Create cases table - matching app.py expectations
    cursor.execute('''
        CREATE TABLE cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT NOT NULL,
            case_type TEXT NOT NULL,
            filing_year INTEGER NOT NULL,
            petitioner TEXT,
            respondent TEXT,
            status TEXT,
            next_date TEXT,
            search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✓ Created 'cases' table")
    
    # Create orders table - matching app.py expectations
    cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER,
            order_date TEXT,
            order_text TEXT,
            pdf_url TEXT,
            pdf_filename TEXT,
            pdf_text TEXT,
            FOREIGN KEY (case_id) REFERENCES cases (id)
        )
    ''')
    print("✓ Created 'orders' table")
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_case_number ON cases(case_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_filing_year ON cases(filing_year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_search_date ON searches(search_date)')
    print("✓ Created database indexes")
    
    # Insert some sample data for demonstration
    print("Inserting sample data...")
    
    # Sample search
    cursor.execute('''
        INSERT INTO searches (case_number, case_type, filing_year)
        VALUES (?, ?, ?)
    ''', ('1234', 'WP(C)', 2023))
    
    # Sample case
    cursor.execute('''
        INSERT INTO cases (case_number, case_type, filing_year, petitioner, 
                          respondent, status, next_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('1234', 'WP(C)', 2023, 'Sample Petitioner', 
          'Sample Respondent', 'Pending', '2024-02-15'))
    
    case_id = cursor.lastrowid
    
    # Sample order
    cursor.execute('''
        INSERT INTO orders (case_id, order_date, order_text, pdf_url)
        VALUES (?, ?, ?, ?)
    ''', (case_id, '2024-01-15', 'Sample order text for case 1234', 
          'https://example.com/sample_order.pdf'))
    
    print("✓ Inserted sample data")
    
    conn.commit()
    conn.close()
    
    print("\nDatabase initialization completed successfully!")
    print("Database file: court_cases.db")
    print("\nSample data:")
    print("- Case: WP(C)/1234/2023")
    print("- Petitioner: Sample Petitioner")
    print("- Respondent: Sample Respondent")
    print("- Status: Pending")
    print("- Next Date: 2024-02-15")

if __name__ == '__main__':
    init_database()
