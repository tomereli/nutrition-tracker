import unittest
from nutrition_tracker import app, generate_mock_data, data
import datetime

class NutritionTrackerTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()  # Flask test client
        self.app.testing = True
        # Clear the data dictionary before each test to prevent test interference
        data.clear()

    def test_add_entry(self):
        response = self.app.post('/addEntry', json={
            'timestamp': '2023-01-01T12:00:00',
            'description': 'Test Food',
            'calories': 500,
            'protein': 30
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Entry added successfully', response.json['message'])

    def test_show_daily(self):
        # Pre-populate mock data
        data.update(generate_mock_data(datetime.date(2023, 1, 1), datetime.date(2023, 1, 7)))
        # Use query parameters to match the mock data date range
        response = self.app.get('/showDaily?start=2023-01-01&end=2023-01-07')
        self.assertEqual(response.status_code, 200)
        self.assertIn('2023-01-01', response.json)

    def test_show_summary(self):
        # Pre-populate mock data
        data.update(generate_mock_data(datetime.date(2023, 1, 1), datetime.date(2023, 1, 7)))
        # Use query parameters to match the mock data date range
        response = self.app.get('/showSummary?start=2023-01-01&end=2023-01-07')
        self.assertEqual(response.status_code, 200)
        self.assertIn('2023-01-01', response.json)

    def test_get_weekly_report(self):
        # Pre-populate mock data
        data.update(generate_mock_data(datetime.date(2023, 1, 1), datetime.date(2023, 1, 7)))
        response = self.app.get('/getWeeklyReport?start=2023-01-01&end=2023-01-07')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<html>', response.data.decode('utf-8'))

if __name__ == '__main__':
    unittest.main()