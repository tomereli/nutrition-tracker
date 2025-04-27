# Nutrition Tracker
A Python Flask application that tracks daily nutrition and workouts, generates HTML reports with:
- Weekly goals (calories, protein, caffeine)
- Daily entries with timestamps and descriptions
- Daily & weekly summaries with colored status
- Daily and weekly scores (1–10)

## Prerequisites
- Python 3.9 or newer (for `zoneinfo`)
- Flask (for web API)

## Setup
```bash
# Unzip the project
unzip nutrition-tracker.zip
cd nutrition-tracker
# (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate   # Windows

# Install required packages
pip install flask
```

## Usage
```bash
# Run the Flask web server
python nutrition_tracker.py

# Run with debug mode and mock data
python nutrition_tracker.py --debug

# Generate mock data and an HTML report for the current week without running server
python nutrition_tracker.py --dump-report
```

The HTML report will be saved to `/tmp/weekly_report_score_colored.html`.

## API Endpoints

### Add a Nutrition Entry
**POST** `/addEntry`
- **Request Body** (application/json):
  ```json
  {
    "timestamp": "string (YYYY-MM-DDThh:mm:ss)",
    "description": "string",
    "calories": "integer",
    "protein": "integer",
    "carbs": "integer (optional)",
    "fat": "integer (optional)",
    "caffeine": "integer (optional)"
  }
  ```
- **Response**:
  - `200`: Success message and the added entry.

### Show Daily Entries
**GET** `/showDaily`
- **Query Parameters**:
  - `start`: Start date (YYYY-MM-DD) - Optional, defaults to the beginning of the current week
  - `end`: End date (YYYY-MM-DD) - Optional, defaults to a week from start or today, whichever is earlier
- **Response**:
  - `200`: JSON with daily entries for the specified date range.
  - `400`: Error if date format is invalid or if start date is after end date.

### Show Summary
**GET** `/showSummary`
- **Query Parameters**:
  - `start`: Start date (YYYY-MM-DD) - Optional, defaults to the beginning of the current week
  - `end`: End date (YYYY-MM-DD) - Optional, defaults to a week from start or today, whichever is earlier
- **Response**:
  - `200`: JSON with daily summaries for the specified date range.
  - `400`: Error if date format is invalid or if start date is after end date.

### Fetch Weekly Report
**GET** `/getWeeklyReport`
- **Query Parameters**:
  - `start`: Start date (YYYY-MM-DD) - Required
  - `end`: End date (YYYY-MM-DD) - Required
- **Response**:
  - `200`: HTML report for the specified date range.
  - `400`: Error if dates are missing, invalid, or if start date is after end date.

### Delete Entry
**POST** `/deleteEntry`
- **Form Parameters**:
  - `date`: Date (YYYY-MM-DD) to delete entries for
- **Response**:
  - `200`: Success message if entries were deleted.
  - `404`: Error if no entries were found for the date.

### Flush All Entries
**POST** `/flushEntries`
- **Response**:
  - `200`: Success message when all entries are cleared.

## Testing
Run the tests using:
```bash
python -m unittest nutrition_tracker_test.py
```

## OpenAPI Specification
The OpenAPI Specification (OAS3) for the API is available in `openapi.yaml`.

## Pushing to GitHub
```bash
git init
git add nutrition_tracker.py README.md
git commit -m "Add nutrition tracker with HTML reporting"
git branch -M main
git remote add origin git@github.com:<username>/nutrition-tracker.git
git push -u origin main
```