import random
from locust import HttpUser, between, task


class PublicPetitionUser(HttpUser):
    wait_time = between(0.3, 1)

    def on_start(self):
        self.petition_ids = []
        with self.client.get("/api/petitions/", name="/api/petitions/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
                return
            try:
                self.petition_ids = [item["id"] for item in response.json()["results"]]
            except (ValueError, KeyError, TypeError):
                response.failure("Unexpected list JSON")
                return
            if not self.petition_ids:
                response.failure("Seed at least one public petition before the load test")

    @task(3)
    def petition_list(self):
        with self.client.get("/api/petitions/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")

    @task
    def petition_detail(self):
        if not self.petition_ids:
            return
        petition_id = random.choice(self.petition_ids)
        with self.client.get(f"/api/petitions/{petition_id}/", name="/api/petitions/{id}/",
                             catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
