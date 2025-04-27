# type: ignore

import datetime
import os
from pathlib import Path
from typing import List, Dict, Any
import random
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify, render_template_string, send_file
import html
from json import JSONEncoder

# ----- Configuration -----
goals = {
    'with_workout': {'calories': 1800, 'protein': 210},
    'without_workout': {'calories': 1600, 'protein': 160},
    'caffeine_max': 400,
    'caffeine_cutoff_hour': 19,
}

# Ensure no variable named 'goals' is redefined elsewhere in the code.
TIME_RANGES = {
    'breakfast': (7, 12),
    'lunch': (12, 15),
    'afternoon': (15, 18),
    'dinner': (18, 21),
    'night': (21, 24),
}
FOODS: Dict[str, List[str]] = {
    'breakfast': ['Omelette', 'Avocado Toast', 'Yogurt & Granola', 'Smoothie Bowl'],
    'lunch':     ['Grilled Chicken Salad', 'Turkey Sandwich', 'Quinoa Bowl', 'Sushi Roll'],
    'afternoon': ['Protein Bar', 'Apple & Peanut Butter', 'Hummus & Veggies'],
    'dinner':    ['Salmon with Veggies', 'Steak & Potatoes', 'Tofu Stir Fry', 'Pasta Primavera'],
    'night':     ['Herbal Tea', 'Cottage Cheese'],
}

DailyData = Dict[datetime.date, List[Dict[str, Any]]]
WeeklySummary = Dict[datetime.date, Dict[str, int]]

# ----- Helpers -----
def summarize_day(entries: List[Dict[str, Any]]) -> Dict[str, int]:
    agg = {k: 0 for k in ['calories', 'protein', 'carbs', 'fat', 'caffeine']}
    for e in entries:
        for k in agg:
            agg[k] += e.get(k, 0)
    return agg

def summarize_week(data: DailyData, start: datetime.date, end: datetime.date) -> WeeklySummary:
    """
    Summarize a week of nutrition data.
    
    Args:
        data: Dictionary mapping dates (as either datetime.date objects or ISO format strings) to daily entries
        start: Start date of the period to summarize
        end: End date of the period to summarize
        
    Returns:
        Dictionary mapping dates to daily summaries
    """
    weekly_summary: WeeklySummary = {}
    current_date = start
    
    while current_date <= end:
        # Try both date object and string format as keys
        entries = []
        
        # Check if the date object is in the data
        if current_date in data:
            entries = data[current_date]
        # Check if the date string is in the data
        else:
            date_str = current_date.isoformat()
            if date_str in data:
                entries = data[date_str]
        
        weekly_summary[current_date] = summarize_day(entries)
        current_date += datetime.timedelta(days=1)
        
    return weekly_summary

# ----- Coloring -----
def color_cal(cons: int, goal: int) -> str:
    diff = cons - goal
    if diff <= 100:
        return 'background-color:lightgreen;'
    if diff < 500:
        return 'background-color:lightyellow;'
    return 'background-color:lightcoral;'

def color_prot(cons: int, goal: int) -> str:
    ratio = cons / goal if goal else 0
    if ratio >= 0.9:
        return 'background-color:lightgreen;'
    if ratio >= 0.8:
        return 'background-color:lightyellow;'
    return 'background-color:lightcoral;'

def color_score(score: float) -> str:
    if score <= 5:
        return 'background-color:lightcoral;'
    elif score < 8:
        return 'background-color:lightyellow;'
    return 'background-color:lightgreen;'

# ----- Scoring -----
def daily_score(cons_cal: int, goal_cal: int, cons_prot: int, goal_prot: int) -> int:
    cal_green = cons_cal - goal_cal <= 100
    prot_green = cons_prot >= 0.9 * goal_prot
    if cal_green and prot_green:
        return 10
    if cal_green or prot_green:
        return 7
    return 4

# ----- Mock Data Generator -----
def generate_mock_data(start: datetime.date, end: datetime.date) -> DailyData:
    data: DailyData = {}
    for i in range((end - start).days + 1):
        day = start + datetime.timedelta(days=i)
        entries = []
        for _ in range(random.randint(3, 6)):
            cat = random.choice(list(TIME_RANGES.keys()))
            hr_start, hr_end = TIME_RANGES[cat]
            hr = random.randint(hr_start, hr_end - 1)
            mn = random.randint(0, 59)
            hour_str = f"{hr:02d}:{mn:02d}"
            food = random.choice(FOODS.get(cat, ['Water']))
            entries.append({
                'hour': hour_str,
                'time': cat,
                'description': food,
                'calories': random.randint(100, 700),
                'protein':  random.randint(5, 50),
                'carbs':    random.randint(10, 100),
                'fat':      random.randint(5, 30),
                'caffeine': random.randint(0, 150) if cat != 'night' else 0,
            })
        data[day] = sorted(entries, key=lambda x: x['hour'])
    return data

# ----- HTML Report Generation -----
def generate_html(daily_data: DailyData, weekly_summary: WeeklySummary,
                  start: datetime.date, end: datetime.date, output_path: str) -> None:
    # Validate date range
    if start > end:
        raise ValueError("Start date must be before or equal to end date.")

    # Check if data is empty
    if not daily_data or not weekly_summary:
        raise ValueError("No data available to generate the report.")

    html_content = ['<html><head><meta charset="utf-8"><title>Nutrition Report</title></head><body>']
    html_content.append(f'<h1>Nutrition Tracking: {start} to {end}</h1>')
    html_content.append('<h2>Weekly Goals</h2><ul>')
    html_content.append(f'<li>Calories: {goals["without_workout"]["calories"]} (up to {goals["with_workout"]["calories"]} on workout days)</li>')
    html_content.append(f'<li>Protein: {goals["without_workout"]["protein"]}g (up to {goals["with_workout"]["protein"]}g on workout days)</li>')
    html_content.append(f'<li>Caffeine: ≤{goals["caffeine_max"]}mg/day; none after {goals["caffeine_cutoff_hour"]}:00</li></ul>')

    # Weekly summary table
    html_content.append('<h2>Weekly Summary</h2><table border="1" cellpadding="5" cellspacing="0">')
    html_content.append('<tr><th>Day</th><th>Date</th><th>Calories</th><th>Protein</th>'
                        '<th>Carbs</th><th>Fat</th><th>Caffeine</th><th>Score</th></tr>')
    total_cal = total_prot = total_score = 0
    days = len(weekly_summary)

    for day in sorted(weekly_summary):
        sums = weekly_summary[day]
        gcal = goals['without_workout']['calories']
        gprot = goals['without_workout']['protein']
        score = daily_score(sums['calories'], gcal, sums['protein'], gprot)
        total_cal += sums['calories']
        total_prot += sums['protein']
        total_score += score
        html_content.append(
            f'<tr>'
            f'<td>{day.strftime("%A")}</td><td>{day}</td>'
            f'<td style="{color_cal(sums["calories"], gcal)}">{sums["calories"]}/{gcal}</td>'
            f'<td style="{color_prot(sums["protein"], gprot)}">{sums["protein"]}/{gprot}</td>'
            f'<td>{sums["carbs"]}</td><td>{sums["fat"]}</td><td>{sums["caffeine"]}</td>'
            f'<td style="{color_score(score)}">{score}</td>'
            f'</tr>'
        )

    avg_score = round(total_score / days, 1) if days else 0
    wcal_goal = goals['without_workout']['calories'] * days
    wprot_goal = goals['without_workout']['protein'] * days
    html_content.append(
        '<tr style="font-weight:bold;">'
        f'<td colspan="2">Totals</td>'
        f'<td style="{color_cal(total_cal, wcal_goal)}">{total_cal}/{wcal_goal}</td>'
        f'<td style="{color_prot(total_prot, wprot_goal)}">{total_prot}/{wprot_goal}</td>'
        f'<td colspan="3"></td>'
        f'<td style="{color_score(avg_score)}">{avg_score}</td>'
        '</tr>'
    )
    html_content.append('</table>')

    # Daily detail sections
    for day in sorted(daily_data):
        sums = weekly_summary[day]
        gcal = goals['without_workout']['calories']
        gprot = goals['without_workout']['protein']
        score = daily_score(sums['calories'], gcal, sums['protein'], gprot)
        html_content.append(f'<h3>{day.strftime("%A")}, {day} (Score: {score})</h3>')
        html_content.append('<table border="1" cellpadding="5" cellspacing="0">')
        html_content.append('<tr><th>Hour</th><th>Time</th><th>Description</th><th>Cal</th>'
                            '<th>Prot</th><th>Carb</th><th>Fat</th><th>Caf</th></tr>')
        for e in daily_data[day]:
            html_content.append(
                f'<tr><td>{e["hour"]}</td><td>{e["time"]}</td><td>{html.escape(e["description"])}</td>'
                f'<td>{e["calories"]}</td><td>{e["protein"]}</td>'
                f'<td>{e["carbs"]}</td><td>{e["fat"]}</td><td>{e["caffeine"]}</td></tr>'
            )
        html_content.append(
            '<tr style="font-weight:bold;">'
            f'<td colspan="3">Total</td>'
            f'<td style="{color_cal(sums["calories"], gcal)}">{sums["calories"]}/{gcal}</td>'
            f'<td style="{color_prot(sums["protein"], gprot)}">{sums["protein"]}/{gprot}</td>'
            f'<td>{sums["carbs"]}</td><td>{sums["fat"]}</td><td>{sums["caffeine"]}</td>'
            '</tr>'
        )
        html_content.append('</table>')

    html_content.append('</body></html>')

    # Write to file
    try:
        os.makedirs(Path(output_path).parent, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_content))
    except Exception as e:
        raise IOError(f"Failed to write HTML report to {output_path}: {e}") from e

app = Flask(__name__)

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return super().default(obj)

app.json_encoder = CustomJSONEncoder

data = {}

# HTML template for the UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nutrition Tracker</title>
    <style>
        .form-group {
            margin-bottom: 10px;
        }
        .section {
            border: 1px solid #ccc;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .date-range {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <h1>Nutrition Tracker</h1>
    
    <div class="section">
        <h2>Add Entry</h2>
        <form action="/addEntry" method="post">
            <div class="form-group">
                <label>Timestamp: <input type="text" name="timestamp" placeholder="YYYY-MM-DDThh:mm:ss" required></label>
            </div>
            <div class="form-group">
                <label>Description: <input type="text" name="description" required></label>
            </div>
            <div class="form-group">
                <label>Calories: <input type="number" name="calories" required></label>
            </div>
            <div class="form-group">
                <label>Protein: <input type="number" name="protein" required></label>
            </div>
            <div class="form-group">
                <label>Carbs: <input type="number" name="carbs"></label>
            </div>
            <div class="form-group">
                <label>Fat: <input type="number" name="fat"></label>
            </div>
            <div class="form-group">
                <label>Caffeine: <input type="number" name="caffeine"></label>
            </div>
            <button type="submit">Add Entry</button>
        </form>
    </div>

    <div class="section">
        <h2>Delete Entry</h2>
        <form action="/deleteEntry" method="post">
            <div class="form-group">
                <label>Date (YYYY-MM-DD): <input type="text" name="date" required></label>
            </div>
            <button type="submit">Delete Entry</button>
        </form>
    </div>

    <div class="section">
        <h2>Flush All Entries</h2>
        <form action="/flushEntries" method="post">
            <button type="submit">Flush All</button>
        </form>
    </div>

    <div class="section">
        <h2>View Reports</h2>
        
        <h3>Weekly HTML Report</h3>
        <form id="weeklyReportForm" action="/getWeeklyReport" method="get" target="_blank">
            <div class="date-range">
                <label>Start Date: <input type="date" name="start" id="reportStartDate" required></label>
                <label>End Date: <input type="date" name="end" id="reportEndDate" required></label>
            </div>
            <button type="submit">Show Weekly HTML Report</button>
        </form>
        
        <h3>Daily Entries</h3>
        <form id="dailyEntriesForm" action="/showDaily" method="get" target="_blank">
            <div class="date-range">
                <label>Start Date: <input type="date" name="start" id="dailyStartDate"></label>
                <label>End Date: <input type="date" name="end" id="dailyEndDate"></label>
            </div>
            <button type="submit">Show Daily Entries</button>
        </form>
        
        <h3>Summary</h3>
        <form id="summaryForm" action="/showSummary" method="get" target="_blank">
            <div class="date-range">
                <label>Start Date: <input type="date" name="start" id="summaryStartDate"></label>
                <label>End Date: <input type="date" name="end" id="summaryEndDate"></label>
            </div>
            <button type="submit">Show Summary</button>
        </form>
    </div>

    <script>
        // Set default dates (current week) for the forms
        function setDefaultDates() {
            const today = new Date();
            const currentDay = today.getDay(); // 0 is Sunday, 1 is Monday, etc.
            
            // Calculate the start of the week (Monday)
            const startOfWeek = new Date(today);
            startOfWeek.setDate(today.getDate() - (currentDay === 0 ? 6 : currentDay - 1));
            
            // Calculate the end of the week (Sunday)
            const endOfWeek = new Date(startOfWeek);
            endOfWeek.setDate(startOfWeek.getDate() + 6);
            
            // Format dates as YYYY-MM-DD
            const formatDate = (date) => {
                const year = date.getFullYear();
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const day = String(date.getDate()).padStart(2, '0');
                return `${year}-${month}-${day}`;
            };
            
            const startDate = formatDate(startOfWeek);
            const endDate = formatDate(endOfWeek);
            
            // Set default values for all date inputs
            document.getElementById('reportStartDate').value = startDate;
            document.getElementById('reportEndDate').value = endDate;
            document.getElementById('dailyStartDate').value = startDate;
            document.getElementById('dailyEndDate').value = endDate;
            document.getElementById('summaryStartDate').value = startDate;
            document.getElementById('summaryEndDate').value = endDate;
        }
        
        // Call the function when the page loads
        window.onload = setDefaultDates;
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/addEntry', methods=['POST'])
def add_entry():
    body = request.json
    required_fields = ['timestamp', 'description', 'calories', 'protein']

    # Validate required fields
    for field in required_fields:
        if field not in body:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Extract data
    timestamp = body['timestamp']
    description = body['description']
    calories = body['calories']
    protein = body['protein']
    carbs = body.get('carbs', 0)
    fat = body.get('fat', 0)
    caffeine = body.get('caffeine', 0)

    # Add entry to data
    entry = {
        'timestamp': timestamp,
        'description': description,
        'calories': calories,
        'protein': protein,
        'carbs': carbs,
        'fat': fat,
        'caffeine': caffeine
    }

    date = timestamp.split('T')[0]  # Extract date from timestamp
    if date not in data:
        data[date] = []
    data[date].append(entry)

    return jsonify({'message': 'Entry added successfully', 'entry': entry}), 200

@app.route('/deleteEntry', methods=['POST'])
def delete_entry():
    date = request.form.get('date')
    if date in data:
        del data[date]
        return jsonify({'message': f'Entries for {date} deleted successfully.'}), 200
    return jsonify({'error': f'No entries found for {date}.'}), 404

@app.route('/flushEntries', methods=['POST'])
def flush_entries():
    data.clear()
    return jsonify({'message': 'All entries flushed successfully.'}), 200

@app.route('/showDaily', methods=['GET'])
def show_daily():
    # Get start and end dates from query parameters if provided
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    today = datetime.datetime.now(ZoneInfo('Asia/Jerusalem')).date()
    
    # Parse start date if provided, otherwise use beginning of current week
    if start_date:
        try:
            start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid start date format. Use YYYY-MM-DD.'}), 400
    else:
        start = today - datetime.timedelta(days=today.weekday())
    
    # Parse end date if provided, otherwise calculate based on start date
    if end_date:
        try:
            end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid end date format. Use YYYY-MM-DD.'}), 400
    else:
        # Default to a week from start, but don't go beyond today
        potential_end = start + datetime.timedelta(days=6)
        end = min(potential_end, today)
    
    # Validate date range
    if start > end:
        return jsonify({'error': 'Start date must be before or equal to end date.'}), 400
        
    # Filter data based on the date range
    filtered_data = {
        date: entries for date, entries in data.items() 
        if (isinstance(date, datetime.date) and start <= date <= end) or
           (isinstance(date, str) and start <= datetime.datetime.strptime(date, '%Y-%m-%d').date() <= end)
    }
    
    # Convert date keys to strings for JSON serialization
    stringified_data = {
        date.isoformat() if isinstance(date, datetime.date) else date: entries 
        for date, entries in filtered_data.items()
    }
    
    return jsonify(stringified_data), 200

@app.route('/showSummary', methods=['GET'])
def show_summary():
    today = datetime.datetime.now(ZoneInfo('Asia/Jerusalem')).date()
    
    # Get start and end dates from query parameters if provided
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    # Parse start date if provided, otherwise use beginning of current week
    if start_date:
        try:
            start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid start date format. Use YYYY-MM-DD.'}), 400
    else:
        start = today - datetime.timedelta(days=today.weekday())
    
    # Parse end date if provided, otherwise calculate based on start date
    if end_date:
        try:
            end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid end date format. Use YYYY-MM-DD.'}), 400
    else:
        # Default to a week from start, but don't go beyond today
        potential_end = start + datetime.timedelta(days=6)
        end = min(potential_end, today)
    
    # Validate date range
    if start > end:
        return jsonify({'error': 'Start date must be before or equal to end date.'}), 400
        
    # Convert date keys to strings for consistent access
    stringified_data = {date.isoformat(): entries for date, entries in data.items()}
    weekly_summary = summarize_week(stringified_data, start, end)
    stringified_summary = {date.isoformat(): entries for date, entries in weekly_summary.items()}
    return jsonify(stringified_summary), 200

@app.route('/getWeeklyReport', methods=['GET'])
def get_weekly_report():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    download = request.args.get('download', 'false').lower() == 'true'

    if not start_date or not end_date:
        return jsonify({'error': 'Missing required query parameters: start and end'}), 400

    try:
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    if start > end:
        return jsonify({'error': 'Start date must be before or equal to end date.'}), 400

    weekly_summary = summarize_week(data, start, end)
    output_path = '/tmp/weekly_report.html'
    generate_html(data, weekly_summary, start, end, output_path)

    # Return the HTML file either as a downloadable attachment or to display in browser
    if download:
        return send_file(output_path, as_attachment=True, download_name='weekly_report.html', mimetype='text/html')
    else:
        return send_file(output_path, as_attachment=False, mimetype='text/html')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Nutrition Tracker')
    parser.add_argument('--debug', action='store_true', help='Run the server in debug mode with pre-populated mock data')
    parser.add_argument('--dump-report', action='store_true', help='Generate a report and exit without running the server')
    args = parser.parse_args()

    if args.dump_report:
        today = datetime.datetime.now(ZoneInfo('Asia/Jerusalem')).date()
        start = today - datetime.timedelta(days=today.weekday())
        end = start + datetime.timedelta(days=6)
        mock_data = generate_mock_data(start, end)
        summ = summarize_week(mock_data, start, end)
        out = '/tmp/weekly_report_score_colored.html'
        generate_html(mock_data, summ, start, end, out)
        print(f'Report generated: {out}')
    else:
        if args.debug:
            today = datetime.datetime.now(ZoneInfo('Asia/Jerusalem')).date()
            start = today - datetime.timedelta(days=today.weekday())
            end = start + datetime.timedelta(days=6)
            data.update(generate_mock_data(start, end))
        app.run(debug=args.debug, port=8080)
