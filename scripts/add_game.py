#!/usr/bin/env python
"""CLI tool to add games to the database."""

import sqlite3
import sys
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent  
sys.path.insert(0, str(BASE_DIR))                  
from utils.validators import validate_game_data, determine_era, get_next_game_id, is_duplicate_name
from db_connect import get_connection


def add_game(data):
    """Add a game to the database."""
    errors = validate_game_data(data)
    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()

    if is_duplicate_name(cursor,data['name']):
        print(f"Error: Game '{data['name']}' already exists")
        conn.close()
        return False
    
    try:
        game_id = get_next_game_id(cursor)
        era = determine_era(data['release_year'])
        
        cursor.execute('''
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
            data.get('publisher', ''),
            data['game_type'],
            data['platform'],
            data.get('budget'),
            data.get('budget_status', 'Not Disclosed'),
            data.get('file_size'),
            data.get('team_size'),
            data.get('development_time'),
            data.get('metacritic_score'),
            data.get('genre', ''),
            data.get('engine', ''),
            data.get('franchise_name', '')
        ))
        
        conn.commit()
        print(f"Added game: {data['name']} (ID: {game_id})")
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_required_input(prompt):
    """Get required input with validation."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("This field is required. Please enter a value.")


def get_int_input(prompt, required=False):
    """Get integer input with validation."""
    while True:
        value = input(prompt).strip()
        if not value:
            if required:
                print("This field is required. Please enter a number.")
                continue
            return None
        try:
            return int(value)
        except ValueError:
            print("Please enter a valid integer.")


def get_float_input(prompt, required=False):
    """Get float input with validation."""
    while True:
        value = input(prompt).strip()
        if not value:
            if required:
                print("This field is required. Please enter a number.")
                continue
            return None
        try:
            return float(value)
        except ValueError:
            print("Please enter a valid number.")


def interactive_prompt():
    """Interactive mode: prompt for each field."""
    print("\n=== Add New Game ===")
    print("Press Enter to skip optional fields\n")
    
    data = {}
    
    data['name'] = get_required_input("Game Title (required): ")
    data['release_year'] = get_int_input("Release Year (required): ", required=True)
    data['developer'] = get_required_input("Developer (required): ")
    data['platform'] = get_required_input("Platform (required): ")
    data['game_type'] = get_required_input("Game Type - AAA/AA/Indie (required): ")
    
    data['publisher'] = input("Publisher (optional): ").strip() or None
    data['budget'] = get_float_input("Budget in USD (optional): ")
    data['budget_status'] = input("Budget Status - Confirmed/Estimated/Not Disclosed (optional): ").strip() or None
    data['team_size'] = get_int_input("Team Size (optional): ")
    data['development_time'] = get_int_input("Development Time in months (optional): ")
    data['file_size'] = get_float_input("File Size in MB (optional): ")
    data['metacritic_score'] = get_int_input("Metacritic Score 0-100 (optional): ")
    data['genre'] = input("Genre (optional): ").strip() or None
    data['engine'] = input("Engine (optional): ").strip() or None
    data['franchise_name'] = input("Franchise Name (optional): ").strip() or None
    
    return data


def main():
    parser = argparse.ArgumentParser(description='Add a game to the database')
    
    parser.add_argument('--name', help='Game title')
    parser.add_argument('--year', type=int, help='Release year')
    parser.add_argument('--developer', help='Developer')
    parser.add_argument('--platform', help='Platform')
    parser.add_argument('--game-type', help='Game type: AAA, AA, or Indie')
    parser.add_argument('--publisher', help='Publisher')
    parser.add_argument('--budget', type=float, help='Budget in USD')
    parser.add_argument('--budget-status', help='Budget status: Confirmed, Estimated, Not Disclosed')
    parser.add_argument('--team-size', type=int, help='Team size')
    parser.add_argument('--dev-time', type=int, help='Development time in months')
    parser.add_argument('--file-size', type=float, help='File size in MB')
    parser.add_argument('--metacritic', type=int, help='Metacritic score 0-100')
    parser.add_argument('--genre', help='Genre')
    parser.add_argument('--engine', help='Engine')
    parser.add_argument('--franchise', help='Franchise name')
    
    args = parser.parse_args()
    
    if args.name or args.year or args.developer or args.platform:
        data = {
            'name': args.name,
            'release_year': args.year,
            'developer': args.developer,
            'platform': args.platform,
            'game_type': args.game_type,
            'publisher': args.publisher,
            'budget': args.budget,
            'budget_status': args.budget_status,
            'team_size': args.team_size,
            'development_time': args.dev_time,
            'file_size': args.file_size,
            'metacritic_score': args.metacritic,
            'genre': args.genre,
            'engine': args.engine,
            'franchise_name': args.franchise
        }
        add_game(data)
    else:
        data = interactive_prompt()
        add_game(data)


if __name__ == '__main__':
    main()