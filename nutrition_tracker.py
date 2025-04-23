import datetime
import csv
import os
from pathlib import Path
from typing import List, Dict, Any
import random
from zoneinfo import ZoneInfo

# ----- Configuration -----
goals = {
    'with_workout': {'calories': 1800, 'protein': 210},
    'without_workout': {'calories': 1600, 'protein': 160},
    'caffeine_max': 400,
    'caffeine_cutoff_hour': 19,
}
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
    summ: WeeklySummary = {}
    d = start
    while d <= end:
        summ[d] = summarize_day(data.get(d, []))
        d += datetime.timedelta(days=1)
    return summ

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
    html = ['<html><head><meta charset="utf-8"><title>Nutrition Report</title></head><body>']
    html.append(f'<h1>Nutrition Tracking: {start} to {end}</h1>')
    html.append('<h2>Weekly Goals</h2><ul>')
    html.append(f'<li>Calories: {goals["without_workout"]["calories"]} (up to {goals["with_workout"]["calories"]} workout days)</li>')
    html.append(f'<li>Protein: {goals["without_workout"]["protein"]}g (up to {goals["with_workout"]["protein"]}g workout days)</li>')
    html.append(f'<li>Caffeine: ≤{goals["caffeine_max"]}mg/day; none after {goals["caffeine_cutoff_hour"]}:00</li></ul>')

    # Weekly summary table
    html.append('<h2>Weekly Summary</h2><table border="1" cellpadding="5" cellspacing="0">')
    html.append('<tr><th>Day</th><th>Date</th><th>Calories</th><th>Protein</th>'
                '<th>Carbs</th><th>Fat</th><th>Caffeine</th><th>Score</th></tr>')
    total_cal = total_prot = total_score = 0
    days = len(weekly_summary)
    for day in sorted(weekly_summary):
        sums   = weekly_summary[day]
        gcal   = goals['without_workout']['calories']
        gprot  = goals['without_workout']['protein']
        score  = daily_score(sums['calories'], gcal, sums['protein'], gprot)
        total_cal  += sums['calories']
        total_prot += sums['protein']
        total_score+= score
        html.append(
            f'<tr>'
            f'<td>{day.strftime("%A")}</td><td>{day}</td>'
            f'<td style="{color_cal(sums["calories"], gcal)}">{sums["calories"]}/{gcal}</td>'
            f'<td style="{color_prot(sums["protein"], gprot)}">{sums["protein"]}/{gprot}</td>'
            f'<td>{sums["carbs"]}</td><td>{sums["fat"]}</td><td>{sums["caffeine"]}</td>'
            f'<td style="{color_score(score)}">{score}</td>'
            f'</tr>'
        )
    avg_score = round(total_score / days, 1) if days else 0
    wcal_goal  = goals['without_workout']['calories'] * days
    wprot_goal = goals['without_workout']['protein'] * days
    html.append(
        '<tr style="font-weight:bold;">'
        f'<td colspan="2">Totals</td>'
        f'<td style="{color_cal(total_cal, wcal_goal)}">{total_cal}/{wcal_goal}</td>'
        f'<td style="{color_prot(total_prot, wprot_goal)}">{total_prot}/{wprot_goal}</td>'
        f'<td colspan="3"></td>'
        f'<td style="{color_score(avg_score)}">{avg_score}</td>'
        '</tr>'
    )
    html.append('</table>')

    # Daily detail sections
    for day in sorted(daily_data):
        sums  = weekly_summary[day]
        gcal  = goals['without_workout']['calories']
        gprot = goals['without_workout']['protein']
        score = daily_score(sums['calories'], gcal, sums['protein'], gprot)
        html.append(f'<h3>{day.strftime("%A")}, {day} (Score: {score})</h3>')
        html.append('<table border="1" cellpadding="5" cellspacing="0">')
        html.append('<tr><th>Hour</th><th>Time</th><th>Description</th><th>Cal</th>'
                    '<th>Prot</th><th>Carb</th><th>Fat</th><th>Caf</th></tr>')
        for e in daily_data[day]:
            html.append(
                f'<tr><td>{e["hour"]}</td><td>{e["time"]}</td><td>{e["description"]}</td>'
                f'<td>{e["calories"]}</td><td>{e["protein"]}</td>'
                f'<td>{e["carbs"]}</td><td>{e["fat"]}</td><td>{e["caffeine"]}</td></tr>'
            )
        html.append(
            '<tr style="font-weight:bold;">'
            f'<td colspan="3">Total</td>'
            f'<td style="{color_cal(sums["calories"], gcal)}">{sums["calories"]}/{gcal}</td>'
            f'<td style="{color_prot(sums["protein"], gprot)}">{sums["protein"]}/{gprot}</td>'
            f'<td>{sums["carbs"]}</td><td>{sums["fat"]}</td><td>{sums["caffeine"]}</td>'
            '</tr>'
        )
        html.append('</table>')

    os.makedirs(Path(output_path).parent, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('
'.join(html))

if __name__ == '__main__':
    today = datetime.datetime.now(ZoneInfo('Asia/Jerusalem')).date()
    start = today - datetime.timedelta(days=today.weekday())
    end   = start + datetime.timedelta(days=6)
    data = generate_mock_data(start, end)
    summ = summarize_week(data, start, end)
    out  = '/mnt/data/weekly_report_score_colored.html'
    generate_html(data, summ, start, end, out)
    print(f'Report generated: {out}')
