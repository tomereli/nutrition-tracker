# Nutrition Tracker

A Python script that tracks daily nutrition and workouts, generates HTML reports with:
- Weekly goals (calories, protein, caffeine)
- Daily entries with timestamps and descriptions
- Daily & weekly summaries with colored status
- Daily and weekly scores (1–10)

## Prerequisites

- Python 3.9 or newer (for `zoneinfo`)
- No external dependencies

## Setup

```bash
# Unzip the project
unzip nutrition-tracker.zip
cd nutrition-tracker

# (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate   # Windows
```

## Usage

```bash
# Generate mock data and an HTML report for the current week
python nutrition_tracker.py

# For a specific week (Monday to Sunday), you can modify the dates in the main section
# or adapt the script to accept CLI arguments.
```

The HTML report will be saved to `/mnt/data/weekly_report_score_colored.html`.

## Pushing to GitHub

```bash
git init
git add nutrition_tracker.py README.md
git commit -m "Add nutrition tracker with HTML reporting"
git branch -M main
git remote add origin git@github.com:<username>/nutrition-tracker.git
git push -u origin main
```