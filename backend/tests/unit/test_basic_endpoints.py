"""Tests for basic API endpoints."""
import pytest


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_read_root(self, client):
        """Test GET / returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Riftventory API"}


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test GET /health returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
