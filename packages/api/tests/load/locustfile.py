"""
SonarFT API load tests — run with locust.

Usage:
    pip install locust
    locust -f tests/load/locustfile.py --host http://localhost:8000

Pass criteria (50 concurrent users):
    GET /health          p99 < 10ms
    GET /clients/.../bots  p99 < 50ms
    GET .../orders       p99 < 500ms
    Error rate           0%
"""
from locust import HttpUser, between, task

_HEADERS = {"Authorization": "Bearer test-token"}
_CLIENT = "test-client"
_BOT = "test-bot"


class ApiUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(10)
    def health(self) -> None:
        self.client.get("/api/v1/health")

    @task(5)
    def ready(self) -> None:
        self.client.get("/api/v1/health/ready")

    @task(3)
    def list_bots(self) -> None:
        self.client.get(
            f"/api/v1/clients/{_CLIENT}/bots",
            headers=_HEADERS,
        )

    @task(1)
    def get_orders(self) -> None:
        self.client.get(
            f"/api/v1/clients/{_CLIENT}/bots/{_BOT}/orders?limit=100",
            headers=_HEADERS,
        )

    @task(1)
    def get_trades(self) -> None:
        self.client.get(
            f"/api/v1/clients/{_CLIENT}/bots/{_BOT}/trades?limit=100",
            headers=_HEADERS,
        )

    @task(1)
    def get_parameters(self) -> None:
        self.client.get(
            f"/api/v1/clients/{_CLIENT}/parameters",
            headers=_HEADERS,
        )
