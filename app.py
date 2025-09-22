# app.py
from flask import Flask, request, jsonify
from datetime import date, datetime
import json
import os

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), '.')

# Load seasons and ZIP->WMU mapping on startup
with open(os.path.join(DATA_DIR, 'pa_seasons_2025_26.json')) as f:
    SEASONS_DB = json.load(f)['seasons']

with open(os.path.join(DATA_DIR, 'sample_zip_to_wmu.json')) as f:
    ZIP_MAP = json.load(f)

def parse_iso(d):
    return datetime.strptime(d, "%Y-%m-%d").date()

def is_date_in_range(today, start_s, end_s):
    start = parse_iso(start_s)
    end = parse_iso(end_s)
    return start <= today <= end

def current_seasons_for_wmu(wmu, waterfowl_zone, today=None):
    if today is None:
        today = date.today()
    results = []
    for s in SEASONS_DB:
        applies = s.get('applies_to')
        match = False

        # Handle string applies_to
        if isinstance(applies, str):
            if applies == 'statewide':
                match = True
            elif applies.lower().endswith('_zone'):
                if waterfowl_zone and applies == waterfowl_zone:
                    match = True
            else:
                if wmu and applies.lower() == wmu.lower():
                    match = True

        # Handle list applies_to
        elif isinstance(applies, list):
            if wmu and any(wmu.lower() == a.lower() for a in applies):
                match = True

        if not match:
            continue

        # Check date ranges
        for r in s.get('date_ranges', []):
            if is_date_in_range(today, r['start'], r['end']):
                out = {
                    'id': s['id'],
                    'species': s['species'],
                    'method': s.get('method'),
                    'start': r['start'],
                    'end': r['end'],
                    'notes': s.get('notes')
                }
                results.append(out)
                break
    return results

@app.after_request
def add_cors_headers(response):
    # Allow cross-origin requests from any domain
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/v1/seasons', methods=['GET'])
def seasons_lookup():
    zip_code = request.args.get('zip', '').strip()
    if not zip_code:
        return jsonify({'error':'missing zip parameter'}), 400

    zip_code = zip_code[:5]  # Normalize 5-digit
    if zip_code not in ZIP_MAP:
        return jsonify({'error':'zip not found in local mapping. Load a full ZIP->WMU dataset.'}), 404

    loc = ZIP_MAP[zip_code]
    wmu = loc.get('wmu')
    waterfowl_zone = loc.get('waterfowl_zone')
    today = date.today()

    seasons = current_seasons_for_wmu(wmu, waterfowl_zone, today)
    return jsonify({
        'zip': zip_code,
        'location': loc,
        'date': today.isoformat(),
        'open_seasons': seasons
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
