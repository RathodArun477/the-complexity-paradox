import sqlite3
import pandas as pd
import os
import sys
from pathlib import Path

#Path Handling
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE_DIR / 'scripts'))

from db_connect import get_connection

#Column mapping: Excel name -> Database name
COLUMN_MAP = {
    'Game Id': 'game_id',
    'Name' : 'name',
    'Release Year' : 'release_year',
    'Era' : 'era',
    'Developer' : 'developer',
    'Publisher' : 'publisher',
    'Game Type' : 'game_type',
    'Genre' : 'genre',
    'Platform' : 'platform',
    'Budget' : 'budget',
    'Budget Status' : 'budget_status',
    'File Size' : 'file_size',
    'Peak Team Size': 'peak_team_size',
    'Development Time': 'development_time',
    'Engine': 'engine',
    'Franchise Name': 'franchise_name',
    'Metacritic Score': 'metacritic_score'
}

# Data types for validation
EXPECTED_TYPES = {
    'game_id': str,
    'name': str,
    'release_year': int,
    'era': str,
    'developer': str,
    'publisher': str,
    'game_type': str,
    'genre': str,
    'platform': str,
    'budget': (int, float, type(None)),
    'budget_status': str,
    'file_size': (int, float),
    'peak_team_size': (int, float),
    'development_time': (int, float),
    'engine': str,
    'franchise_name': str,
    'metacritic_score': (int, float, type(None))
}

def validate_row(row,idx):
    """Validate a single row before insertion."""
    errors = []

    for col, expected in EXPECTED_TYPES.items():
        value = row.get(col)
        if value is None or pd.isna(value):
            if col in ['game_id','name','release_year']:
                errors.append(f"Missing required field: {col}")
            continue

        if not isinstance(value,expected):
            errors.append(f"Invalid type for {col}: expected {expected}, got {type(value)}")
    
    if errors:
        print(f"Row {idx} (ID: {row.get('game_id','UNKNOWN')}): {','.join(errors)}")
        return False
    return True

def clean_dataframe(df):
    """Clean and normalize the dataframe before import."""
    #Rename columns using explicit mapping
    df = df.rename(columns=COLUMN_MAP)

    #Strip whitespace from string column
    string_cols = ['game_id', 'name', 'era', 'developer', 'publisher', 'game_type', 'genre', 'platform', 'engine', 'franchise_name', 'budget_status']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    #Handle empty strings as None
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].replace('',None)
    
    #Convert numeric columns, coerce erros to Nan
    numeric_cols = ['release_year', 'budget', 'file_size', 'peak_team_size','development_time', 'metacritic_score']

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col],errors='coerce')
    
    #Drop the header row if it got imported as data
    df = df[df['game_id'] != 'game_id']

    #Remove duplicates game_ids (keep first)
    df = df.drop_duplicates(subset=['game_id'], keep='first')

    return df

def setup_database():
    """Create tables and import data from Excel."""
    conn = get_connection()
    cursor = conn.cursor()

    #Create table with constraints
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            release_year INTEGER NOT NULL,
            era TEXT NOT NULL,
            developer TEXT,
            publisher TEXT,
            game_type TEXT,
            genre TEXT,
            platform TEXT,
            budget REAL,
            budget_status TEXT,
            file_size REAL,
            peak_team_size REAL,
            development_time REAL,
            engine TEXT,
            franchise_name TEXT,
            metacritic_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    #Create indexes for common queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_year ON games(release_year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_era ON games(era)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_type ON games(game_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_metacritic ON games(metacritic_score)')

    #Check existing data
    count = cursor.execute("SELECT COUNT(*) FROM games").fetchone()[0]

    if count == 0:
        excel_path = BASE_DIR / 'data' / 'games_data.xlsx'

        if not excel_path.exists():
            print(f"ERROR: Excel file not found at {excel_path}")
            conn.close()
            return
        
        try:
            #Read Excel, skip the duplicates header row if present
            df = pd.read_excel(excel_path,sheet_name='Games Information')

            #Clean and validate
            df = clean_dataframe(df)

            #Validates each row
            valid_rows = []
            for idx, row in df.iterrows():
                if validate_row(row,idx):
                    valid_rows.append(row)

            if not valid_rows:
                print("ERROR: No valid rows found after validataion")
                conn.close()
                return
            
            df_valid = pd.DataFrame(valid_rows)

            #Insert into database
            df_valid.to_sql('games',conn, if_exists='append',index=False)

            final_count = cursor.execute("SELECT COUNT(*) FROM games").fetchone()[0]
            print(f"Imported {len(df_valid)} games successfully")
            print(f"Total Games in database: {final_count}")
        
        except Exception as e:
            import traceback
            print(f"ERROR during import: {e}")
            traceback.print_exc()
            conn.rollback()
    else:
        print(f"Database already has {count} games, skipping import")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    setup_database()
