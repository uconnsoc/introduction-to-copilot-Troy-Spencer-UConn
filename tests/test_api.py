"""
Tests for the Mergington High School Activities API

Tests all endpoints including happy paths and error cases.
Uses fixtures to ensure test isolation and clean state between tests.
"""

import pytest
from copy import deepcopy
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        },
    }
    
    # Clear current activities and restore fresh state
    activities.clear()
    activities.update(deepcopy(original_activities))
    
    yield activities
    
    # Cleanup after test
    activities.clear()
    activities.update(deepcopy(original_activities))


@pytest.fixture
def client(reset_activities):
    """Provide a test client for making requests"""
    return TestClient(app)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test successful retrieval of all activities"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all activities are returned
        assert len(data) == 3
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        # Check structure of an activity
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=new_student@mergington.edu",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "new_student@mergington.edu" in data["message"]
        
        # Verify participant was added
        assert "new_student@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu",
            json={}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_already_registered(self, client):
        """Test that duplicate signup returns 400 error"""
        # Try to sign up someone already registered
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu",
            json={}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_multiple_students(self, client, reset_activities):
        """Test that multiple different students can sign up"""
        # First student signs up
        response1 = client.post(
            "/activities/Chess Club/signup?email=student1@mergington.edu",
            json={}
        )
        assert response1.status_code == 200
        
        # Second student signs up
        response2 = client.post(
            "/activities/Chess Club/signup?email=student2@mergington.edu",
            json={}
        )
        assert response2.status_code == 200
        
        # Verify both are registered
        assert "student1@mergington.edu" in activities["Chess Club"]["participants"]
        assert "student2@mergington.edu" in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == 4  # 2 original + 2 new


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister from an activity"""
        # Verify student is registered
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        
        # Unregister
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        
        # Verify participant was removed
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_activity_not_found(self, client):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=student@mergington.edu"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_unregister_student_not_registered(self, client):
        """Test unregister for student not registered returns 400"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]
    
    def test_unregister_all_participants(self, client, reset_activities):
        """Test unregistering all participants from an activity"""
        original_participants = activities["Chess Club"]["participants"].copy()
        
        # Unregister each participant
        for email in original_participants:
            response = client.delete(
                f"/activities/Chess Club/unregister?email={email}"
            )
            assert response.status_code == 200
        
        # Verify activity has no participants
        assert len(activities["Chess Club"]["participants"]) == 0


class TestIntegration:
    """Integration tests combining multiple operations"""
    
    def test_signup_then_unregister(self, client, reset_activities):
        """Test signup followed by unregister"""
        email = "integration_test@mergington.edu"
        
        # Sign up
        signup_response = client.post(
            f"/activities/Programming Class/signup?email={email}",
            json={}
        )
        assert signup_response.status_code == 200
        assert email in activities["Programming Class"]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/Programming Class/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        assert email not in activities["Programming Class"]["participants"]
    
    def test_signup_unregister_resigning(self, client, reset_activities):
        """Test that a student can unregister and then re-signup"""
        email = "resigning_student@mergington.edu"
        
        # First signup
        response1 = client.post(
            f"/activities/Gym Class/signup?email={email}",
            json={}
        )
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.delete(
            f"/activities/Gym Class/unregister?email={email}"
        )
        assert response2.status_code == 200
        
        # Re-signup
        response3 = client.post(
            f"/activities/Gym Class/signup?email={email}",
            json={}
        )
        assert response3.status_code == 200
        assert email in activities["Gym Class"]["participants"]
