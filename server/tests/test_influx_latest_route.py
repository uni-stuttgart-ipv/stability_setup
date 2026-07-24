import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routes import router


class LatestInfluxRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api/v1")
        self.client = TestClient(self.app)

    def test_latest_measurement_endpoint_returns_latest_row(self):
        class FakeInfluxClient:
            def query(self, query, database=None, **kwargs):
                self.last_query = query
                self.last_database = database
                return [{"time": "2026-07-23T10:00:00Z", "temperature": 42.5, "status": "ok"}]

        fake_client = FakeInfluxClient()

        with patch("app.api.v1.routes.get_influx_client", return_value=fake_client):
            response = self.client.get("/api/v1/influx/latest/temperature?bucket=test-bucket")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["measurement"], "temperature")
        self.assertEqual(response.json()["bucket"], "test-bucket")
        self.assertEqual(response.json()["values"]["temperature"], 42.5)
        self.assertIn("SELECT", fake_client.last_query)
        self.assertEqual(fake_client.last_database, "test-bucket")


if __name__ == "__main__":
    unittest.main()
