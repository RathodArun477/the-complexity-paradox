"""Shared validation utilities for game data.
Used by add_game.py CLI and Flask admin routes."""

from datetime import datetime

def validate_game_data(data):
    """Validate game data before insertion.
    
    Args:
        data: dict with game fields
    
    Returns:
        list of error strings (empty if valid)
    """

    errors = []

    #Required fields
    required = ['name','release_year','developer','platform','game_type']
    for field in required:
        if not data.get(field):
            errors.append(f"{field} is required")

    # Release Year
    year = data.get('release_year')
    if year is not None:
        current_year = datetime.now().year
        if year < 1970 or year > current_year + 5:
            errors.append(f"release_year must be between 1970 and {current_year + 5}")

    # Game Type enum
    game_type = data.get('game_type')
    if game_type and game_type not in ('AAA','AA','Indie'):
        errors.append("game_type must be AAA, AA, or Indie")

    # Team size
    team_size = data.get('team_size')
    if team_size is not None and team_size < 1:
        errors.append("team_size must be at least 1")
    
    # Development time
    dev_time = data.get('development_time')
    if dev_time is not None and dev_time < 1:
        errors.append("devlopment_time must be at least 1 month")

    # File size
    file_size = data.get('file_size')
    if file_size is not None and file_size < 0:
        errors.append("file_size cannot be negative")

    # Budget (optional but validated if present)
    budget = data.get('budget')
    if budget is not None and budget < 0:
        errors.append("budget cannot be negative")

    # Metacritic
    metacritic = data.get('metacritic_score')
    if metacritic is not None:
        if metacritic < 0 or metacritic > 100:
            errors.append("metacritic_score must be between 0 and 100")
    
    return errors


def determine_era(year):
    """Determine era from release year."""
    if year < 1990:
        return "1980s"
    elif year < 2000:
        return "1990s"
    elif year < 2010:
        return "2000s"
    elif year < 2020:
        return "2010s"
    else:
        return "2020s"


def get_next_game_id(cursor):
    """Generate next game ID using MAX to avoid collisions after deletes."""
    result = cursor.execute(
        "SELECT MAX(CAST(SUBSTR(game_id, 2) AS INTEGER)) FROM games"
    ).fetchone()[0]
    
    max_id = result or 0
    return f"G{max_id + 1:03d}"

def is_duplicate_name(cursor,name):
    """Check if a game with this name already exists in the database."""
    if not name:
        return False
    result = cursor.execute(
        "SELECT 1 FROM games where LOWER(name) == LOWER(?)",(name.strip(),)
    ).fetchone()
    return result is not None
