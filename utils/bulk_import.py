"""Bulk import utilities for processing Excel/CSV game uploads."""

import pandas as pd
from utils.validators import validate_game_data, determine_era, get_next_game_id, is_duplicate_name


# Expected column names (case-insensitive, flexible matching)
# Supports both database names AND human-readable Excel names
COLUMN_ALIASES = {
    'game_id': ['game_id', 'game id', 'gameid', 'id'],
    'name': ['name', 'game title', 'title', 'game_name'],
    'release_year': ['release_year', 'release year', 'year', 'releaseyear'],
    'developer': ['developer', 'dev', 'studio'],
    'platform': ['platform', 'platforms', 'system'],
    'game_type': ['game_type', 'game type', 'type', 'gametype'],
    'publisher': ['publisher', 'pub'],
    'budget': ['budget', 'cost', 'budget_usd'],
    'budget_status': ['budget_status', 'budget status', 'budgetstatus'],
    'team_size': ['team_size', 'team size', 'peak_team_size', 'peak team size', 'teamsize', 'peak_team'],
    'development_time': ['development_time', 'development time', 'dev_time', 'dev time', 'devtime', 'months'],
    'file_size': ['file_size', 'file size', 'filesize', 'size'],
    'metacritic_score': ['metacritic_score', 'metacritic score', 'metacritic', 'score'],
    'genre': ['genre', 'genres', 'category'],
    'engine': ['engine', 'game_engine', 'game engine'],
    'franchise_name': ['franchise_name', 'franchise name', 'franchise', 'series'],
}

# Reverse map: normalized -> canonical
def build_column_map(df_columns):
    """Build a mapping from uploaded columns to canonical DB field names."""
    col_map = {}
    df_lower = {c.strip().lower().replace(' ', '_'): c for c in df_columns}
    
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_norm = alias.strip().lower().replace(' ', '_')
            if alias_norm in df_lower and canonical not in col_map.values():
                col_map[df_lower[alias_norm]] = canonical
                break
    return col_map


def normalize_columns(df):
    """Normalize DataFrame columns using aliases, then fallback to basic normalization."""
    # First try alias matching
    col_map = build_column_map(df.columns)
    matched = set(col_map.keys())
    unmatched = [c for c in df.columns if c not in matched]
    
    # For unmatched, do basic normalization
    for col in unmatched:
        normalized = col.strip().lower().replace(' ', '_')
        if normalized not in col_map.values():
            col_map[col] = normalized
    
    return df.rename(columns=col_map)


def clean_dataframe(df):
    """Clean and normalize the dataframe before import.
    Adapted from setup_database.py patterns."""
    # Rename columns
    df = normalize_columns(df)
    
    # Strip whitespace from string columns
    string_cols = ['name', 'developer', 'publisher', 'game_type', 'genre', 
                   'platform', 'engine', 'franchise_name', 'budget_status']
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    
    # Handle empty strings as None
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].replace('', None)
            df[col] = df[col].replace('nan', None)  # pandas ast(str) can produce 'nan'
    
    # Convert numeric columns, coerce errors to NaN
    numeric_cols = ['release_year', 'budget', 'file_size', 'team_size',
                    'development_time', 'metacritic_score']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop header row if it got imported as data (common with malformed CSVs)
    if 'name' in df.columns:
        df = df[df['name'] != 'name']
        df = df[df['name'] != 'Name']
        df = df[df['name'] != 'Game Title']
    
    # Remove rows with duplicate names (keep first) — but only check within the upload
    if 'name' in df.columns:
        df = df.drop_duplicates(subset=['name'], keep='first')
    
    return df


def safe_cast(value, cast_type):
    """Safely cast a value, return None on failure."""
    if pd.isna(value):
        return None
    try:
        return cast_type(value)
    except (ValueError, TypeError):
        return None


def build_data_dict(row):
    """Build a clean data dict from a DataFrame row, handling NaN -> None."""
    return {
        'name': str(row.get('name', '')).strip() or None,
        'release_year': safe_cast(row.get('release_year'), int),
        'developer': str(row.get('developer', '')).strip() or None,
        'platform': str(row.get('platform', '')).strip() or None,
        'game_type': str(row.get('game_type', '')).strip() or None,
        'publisher': str(row.get('publisher', '')).strip() or None,
        'budget': safe_cast(row.get('budget'), float),
        'budget_status': str(row.get('budget_status', 'Not Disclosed')).strip() or 'Not Disclosed',
        'team_size': safe_cast(row.get('team_size'), int),
        'development_time': safe_cast(row.get('development_time'), int),
        'file_size': safe_cast(row.get('file_size'), float),
        'metacritic_score': safe_cast(row.get('metacritic_score'), int),
        'genre': str(row.get('genre', '')).strip() or None,
        'engine': str(row.get('engine', '')).strip() or None,
        'franchise_name': str(row.get('franchise_name', '')).strip() or None,
    }


def process_bulk_upload(file_path, db_cursor):
    """Process bulk upload file. Returns {added: int, skipped: list, errors: list}."""
    
    # Read file
    try:
        if str(file_path).lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        return {"added": 0, "skipped": [], "errors": [f"Failed to read file: {str(e)}"]}

    if df.empty:
        return {"added": 0, "skipped": [], "errors": ["File is empty"]}

    # Clean and normalize
    df = clean_dataframe(df)

    # Check for required columns
    required_cols = {'name', 'release_year', 'developer', 'platform', 'game_type'}
    available_cols = set(df.columns)
    missing_required = required_cols - available_cols
    if missing_required:
        return {
            "added": 0,
            "skipped": [],
            "errors": [f"Missing required columns: {', '.join(missing_required)}"]
        }

    added = 0
    skipped = []
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # +2 for header row and 0-based index
        data = build_data_dict(row)

        # Skip rows with no name (likely blank lines)
        if not data.get('name'):
            skipped.append({
                "row": row_num,
                "name": "(blank)",
                "reason": "No game name provided"
            })
            continue

        # Validate
        validation_errors = validate_game_data(data)
        if validation_errors:
            skipped.append({
                "row": row_num,
                "name": data['name'],
                "reason": "; ".join(validation_errors)
            })
            continue

        # Check duplicate against database
        if is_duplicate_name(db_cursor, data['name']):
            skipped.append({
                "row": row_num,
                "name": data['name'],
                "reason": f"Game '{data['name']}' already exists in database"
            })
            continue

        # Insert
        try:
            game_id = get_next_game_id(db_cursor)
            era = determine_era(data['release_year'])

            db_cursor.execute('''
                INSERT INTO games (
                    game_id, name, release_year, era, developer, publisher,
                    game_type, platform, budget, budget_status, file_size, peak_team_size,
                    development_time, metacritic_score, genre, engine, franchise_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_id,
                data['name'],
                data['release_year'],
                era,
                data['developer'],
                data.get('publisher') or '',
                data['game_type'],
                data['platform'],
                data.get('budget'),
                data.get('budget_status', 'Not Disclosed'),
                data.get('file_size'),
                data.get('team_size'),
                data.get('development_time'),
                data.get('metacritic_score'),
                data.get('genre') or '',
                data.get('engine') or '',
                data.get('franchise_name') or ''
            ))
            added += 1

        except Exception as e:
            skipped.append({
                "row": row_num,
                "name": data.get('name') or f"Unnamed (row {row_num})",
                "reason": f"Database error: {str(e)}"
            })

    return {
        "added": added,
        "skipped": skipped,
        "errors": errors
    }