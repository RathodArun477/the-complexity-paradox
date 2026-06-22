from flask import Flask, render_template, jsonify, g, request, redirect, send_file, url_for, flash
import sqlite3
import pandas as pd
import numpy as np
import sys
import os
import subprocess
import tempfile
from pathlib import Path
import io
from datetime import datetime
from dotenv import load_dotenv

# Path Handling
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(PROJECT_ROOT))
sys.path.insert(0,str(PROJECT_ROOT / 'scripts'))

from db_connect import get_connection
from utils.formatters import register_filters
from utils.validators import validate_game_data, determine_era, get_next_game_id, is_duplicate_name
from utils.bulk_import import process_bulk_upload

load_dotenv(PROJECT_ROOT / '.env')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
register_filters(app)

ADMIN_KEY = os.environ.get('ADMIN_KEY')

def get_db():
    """Get database connection, stored in Flask's g object for request lifecycle."""
    if 'db' not in g:
        g.db = get_connection()
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Close connection after each request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_games():
    """Reusable query function with error handling."""
    try:
        df = pd.read_sql_query("SELECT * FROM games", get_db())
        return df.to_dict(orient='records')
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        app.logger.error(f"Database error: {e}")
        return None
    
def query_games_paginated(page=1, per_page=20,search=None):
    """Query games with pagination and optional searchs."""
    try:
        offset = (page - 1) * per_page
        db = get_db()
        cursor = db.cursor()

        # Build query
        if search:
            search_term = f"%{search}%"
            where_clause = "WHERE name LIKE ? OR developer LIKE ? OR platform LIKE ?"
            count_sql = f"SELECT COUNT(*) FROM games {where_clause}"

            total = cursor.execute(count_sql, (search_term,search_term, search_term)).fetchone()[0]

            data_sql = f"SELECT * FROM games {where_clause} LIMIT ? OFFSET ?"

            df = pd.read_sql_query(data_sql,db,params=(search_term,search_term,search_term,per_page,offset))
        else:
            total = cursor.execute("SELECT COUNT(*) FROM games").fetchone()[0]

            df = pd.read_sql_query("SELECT * FROM games LIMIT ? OFFSET ?",db, params=(per_page,offset))

        return {
            'games': df.to_dict(orient='records'),
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': max(1, (total + per_page - 1) // per_page),
            'search': search
        }
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        app.logger.error(f"Database error: {e}")
        return None


# PUBLIC ROUTES

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html')

@app.route('/explore')
def explore():
    page = request.args.get('page',1,type=int)
    per_page = request.args.get('per_page',20,type=int)
    search = request.args.get('search',None)

    result = query_games_paginated(page,per_page,search)
    if result is None:
        return "Database error", 500
    
    return render_template('explore.html',**result)

@app.route('/about')
def about():
    return render_template('about.html')

#API ROUTES

@app.route('/api/games')
def api_games():
    games = query_games()
    if games is None:
        return jsonify({"error": "Database error"}), 500
    return jsonify(games)

@app.route('/game/<game_id>')
def game_detail(game_id):
    """Show detailed info for a single game."""
    try:
        df = pd.read_sql_query(
            "SELECT * FROM games WHERE game_id = ?",
            get_db(),
            params=(game_id,)
        )
        if df.empty:
            return "Game not found", 404
        
        game = df.iloc[0].to_dict()
        return render_template('game_detail.html', game=game)
    
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        app.logger.error(f"Database error: {e}")
        return "Database error", 500

@app.route('/api/chart/q1')
def chart_q1():
    """Development time over years - scatter by game type + trend line."""
    try:
        df = pd.read_sql_query("SELECT * FROM games",get_db())
        df = df.dropna(subset=['development_time','release_year','game_type'])

        datasets = []
        colors = {'AAA' : '#e74c3c', 'AA' : '#3498db', 'Indie': '#2ecc71'}
        
        for game_type in ['AAA','AA','Indie']:
            subset = df[df['game_type'] == game_type]
            points = [
                {'x' : int(row['release_year']),'y':float(row['development_time']),'name': row['name']}
                for _, row in subset.iterrows()
            ]

            datasets.append({
                'label' : game_type,
                'data' : points,
                'backgroundColor' : colors.get(game_type,'#999'),
                'borderColor' : colors.get(game_type, '#999'),
                'pointRadius' : 6,
                'pointHoverRadius' : 8
            })

        # Trend line (linear regression)
        z = np.polyfit(df['release_year'],df['development_time'],1)
        p = np.poly1d(z)
        x_min, x_max = int(df['release_year'].min()), int(df['release_year'].max())
        trend = [
            {'x' : x, 'y' : float(p(x))}
            for x in range(x_min,x_max + 1,5)
        ]

        return jsonify({
            'datasets' : datasets,
            'trend' : trend,
            'x_min' : x_min,
            'x_max' : x_max
        })
    
    except Exception as e:
        app.logger.error(f"Chart q1 error: {e}")
        return jsonify({"error" : str(e)}),500

@app.route('/api/chart/q3')
def chart_q3():
    """Era comparison - dual axis bar chart for dev time and team size."""
    try:
        df = pd.read_sql_query("SELECT * FROM games",get_db())
        # print("Columns:",df.columns.tolist()) # Debug
        # print("Sample data:",df[['era','development_time','peak_team_size']].head()) #Debug
        df = df.dropna(subset=['development_time','peak_team_size','era'])

        era_order = ['1980s','1990s','2000s','2010s','2020s']

        era_dev_time = df.groupby('era')['development_time'].mean().reindex(era_order)
        era_team_size = df.groupby('era')['peak_team_size'].mean().reindex(era_order)

        return jsonify({
            'labels' : era_order,
            'dev_time' : [float(v) if not pd.isna(v) else 0 for v in era_dev_time.values],
            'team_size' : [float(v) if not pd.isna(v) else 0 for v in era_team_size.values]
        })
    
    except Exception as e:
        import traceback
        app.logger.error(f"Charts Q3 error: {e}")
        traceback.print_exc() # Full traceback
        return jsonify({"error" : str(e)}),500
    
@app.route('/api/chart/q7')
def chart_q7():
    """Engine efficiency - box plot equivalent with bar chart."""
    try:
        df = pd.read_sql_query("SELECT * FROM games",get_db())
        df = df.dropna(subset=['development_time','engine'])

        #Categorize engines
        def categorize_engine(engine):
            if 'Unreal' in str(engine):
                return 'Unreal'
            elif engine == 'Unity':
                return 'Unity'
            elif engine == 'Source':
                return 'Source'
            elif engine == 'Proprietary':
                return 'Proprietary'
            else:
                return 'Other Licensed'
        
        df['engine_category'] = df['engine'].apply(categorize_engine)

        #Calculate averages per category
        avg_dev = df.groupby('engine_category')['development_time'].mean().sort_values()

        return jsonify({
            'labels': avg_dev.index.tolist(),
            'values': [float(v) for v in avg_dev.values]
        })
    
    except Exception as e:
        import traceback
        app.logger.error(f"Chart Q7 error: {e}")
        traceback.print_exc()
        return jsonify({"error":str(e)}),500

@app.route('/api/chart/q8')
def chart_q8():
    """Indie vs AAA divergence - 4 metrics over decades."""
    try:
        df = pd.read_sql_query("SELECT * FROM games",get_db())
        df = df[df['game_type'].isin(['Indie','AAA'])].copy()

        era_order = ['1980s','1990s','2000s','2010s','2020s']
        metrics = ['development_time','budget','peak_team_size','file_size']

        result = {}
        for metric in metrics:
            result[metric] = {}
            for game_type in ['AAA','Indie']:
                subset = df[df['game_type'] == game_type].dropna(subset=[metric])

                era_avg = subset.groupby('era')[metric].mean().reindex(era_order)
                result[metric][game_type] = [
                    float(v) if not pd.isna(v) else None
                    for v in era_avg.values
                ] 

        return jsonify({
            'labels': era_order,
            'metrics': result
        })
    except Exception as e:
        app.logger.error(f"Chart Q8 error: {e}")
        return jsonify({"error" : str(e)}),500


@app.route('/api/test')
def test():
    return jsonify({"status" : "ok"})


#ADMIN ROUTES

def check_admin_key():
    """Simple key-based auth."""
    return request.args.get('key') == ADMIN_KEY or request.form.get('key') == ADMIN_KEY

@app.route('/admin')
def admin():
    """Admin dashboard"""
    if not check_admin_key():
        return "Not Found", 404
    return render_template('admin.html')

@app.route('/admin/add-game', methods=['POST'])
def admin_add_game():
    """Add a game and regenerate charts in one blocking call."""
    if not check_admin_key():
        return "Not found", 404

    # Build data from form
    data = {
        'name': request.form.get('name'),
        'release_year': request.form.get('release_year', type=int),
        'developer': request.form.get('developer'),
        'platform': request.form.get('platform'),
        'game_type': request.form.get('game_type'),
        'publisher': request.form.get('publisher') or None,
        'budget': request.form.get('budget', type=float) or None,
        'budget_status': request.form.get('budget_status') or 'Not Disclosed',
        'team_size': request.form.get('team_size', type=int) or None,
        'development_time': request.form.get('development_time', type=int) or None,
        'file_size': request.form.get('file_size', type=float) or None,
        'metacritic_score': request.form.get('metacritic_score', type=int) or None,
        'genre': request.form.get('genre') or None,
        'engine': request.form.get('engine') or None,
        'franchise_name': request.form.get('franchise_name') or None,
    }

    # Validate
    errors = validate_game_data(data)
    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    db = get_db()
    cursor = db.cursor()

    if is_duplicate_name(cursor, data['name']):
        return jsonify({
            "success": False,
            "errors": [f"Game '{data['name']}' already exists"]
        }), 400

    try:
        # Insert game
        game_id = get_next_game_id(cursor)
        era = determine_era(data['release_year'])

        cursor.execute('''
            INSERT INTO games (
                game_id, name, release_year, era, developer, publisher,
                game_type, platform, budget, budget_status, file_size, peak_team_size,
                development_time, metacritic_score, genre, engine, franchise_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            game_id, data['name'], data['release_year'], era,
            data['developer'], data.get('publisher', ''),
            data['game_type'], data['platform'],
            data.get('budget'), data.get('budget_status', 'Not Disclosed'),
            data.get('file_size'), data.get('team_size'),
            data.get('development_time'), data.get('metacritic_score'),
            data.get('genre', ''), data.get('engine', ''),
            data.get('franchise_name', '')
        ))
        db.commit()

        # Regenerate charts (blocking)
        script_path = PROJECT_ROOT / 'notebooks' / 'generate_charts.py'
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT / 'notebooks')
        )

        if result.returncode != 0:
            return jsonify({
                "success": True,
                "game_id": game_id,
                "message": f"Added {data['name']} ({game_id}), but chart regeneration failed: {result.stderr}",
                "charts_ok": False
            }), 500

        return jsonify({
            "success": True,
            "game_id": game_id,
            "message": f"Added {data['name']} ({game_id}). Charts updated.",
            "charts_ok": True,
            "chart_output": result.stdout
        })

    except sqlite3.Error as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    except subprocess.TimeoutExpired:
        return jsonify({
            "success": True,
            "game_id": game_id,
            "message": f"Added {data['name']} ({game_id}), but chart regeneration timed out.",
            "charts_ok": False
        }), 500

@app.route('/admin/bulk-upload',methods=['POST'])
def admin_bulk_upload():
    """Bulk upload games via CSV/Excel. Skip bad rows, refresh charts once."""

    if not check_admin_key():
        return "Not Found", 404
    
    if 'file' not in request.files:
        return jsonify({"success": False, "errors": ["No file uploaded"]}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "errors": ["Empty filename"]}), 400
    
    #Validate extension
    allowed_exts = {'.csv', '.xlsx', '.xls'}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        return jsonify({
            "success": False,
            "errors": [f"Invalid file type. Allowed : {','.join(allowed_exts)}"]
        }), 400
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    
    try:
        db = get_db()
        cursor = db.cursor()

        #Process bulk upload
        result = process_bulk_upload(tmp_path, cursor)

        if result.get("errors") and not result.get("skipped") and result["added"] == 0:
            #Complete failure (file read error, missing columns, etc..)
            return jsonify({
                "success": False,
                "errors": result["errors"]
            }), 400
        
        # Commit if we added anything
        if result["added"] > 0:
            db.commit()

            # Refresh charts once after all inserts
            script_path = PROJECT_ROOT / 'notebooks' / 'generate_charts.py'
            try:
                proc_result = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(PROJECT_ROOT / 'notebooks')
                )
                charts_ok = proc_result.returncode == 0
                chart_output = proc_result.stdout if charts_ok else proc_result.stderr
            
            except subprocess.TimeoutExpired:
                charts_ok = False
                chart_output = "Chart refresh time out."
        else:
            charts_ok = True
            chart_output = "No game added; charts not refreshed."

        return jsonify({
            "success": True,
            "added": result["added"],
            "skipped": result["skipped"],
            "charts_ok": charts_ok,
            "chart_output": chart_output
        })
    
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "errors": [str(e)]}), 500
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

@app.route('/admin/download-template')
def admin_download_template():
    """Download empty CSV/Excel template with correct column headers."""
    if not check_admin_key():
        return "Not found", 404

    file_type = request.args.get('format', 'csv').lower()

    # Column headers using human-readable names (matching setup_database.py's Excel format)
    columns = [
        'Name', 'Release Year', 'Developer', 'Platform', 'Game Type',
        'Publisher', 'Budget', 'Budget Status', 'Team Size', 'Development Time',
        'File Size', 'Metacritic Score', 'Genre', 'Engine', 'Franchise Name'
    ]

    # Empty DataFrame with just headers
    df = pd.DataFrame(columns=columns)

    if file_type == 'xlsx':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Games Information', index=False)
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='games_template.xlsx'
        )
    else:
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='games_template.csv'
        )
        
# ERROR HANDLERS

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True)
