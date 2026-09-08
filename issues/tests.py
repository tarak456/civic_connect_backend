from django.test import TestCase
from accounts.models import User
from issues.models import Department, Issue, Notification
from issues.services.ai_service import CivicAIService


class CivicConnectBackendTests(TestCase):
    def setUp(self):
        self.roads_dept = Department.objects.create(name="Roads Department")
        self.sanitation_dept = Department.objects.create(name="Sanitation Department")

        self.citizen = User.objects.create_user(
            username="testcitizen",
            email="citizen@test.com",
            password="password123",
            role=User.Role.CITIZEN,
            is_verified=True,
        )

        self.admin = User.objects.create_user(
            username="testadmin",
            email="admin@test.com",
            password="password123",
            role=User.Role.GOVERNMENT,
            is_verified=True,
        )

        self.maintainer = User.objects.create_user(
            username="testmaintainer",
            email="maintainer@test.com",
            password="password123",
            role=User.Role.MAINTAINER,
            is_verified=True,
        )

    def test_ai_classification_and_severity(self):
        result = CivicAIService.analyze(
            description="Deep emergency pothole on asphalt road causing danger to vehicles",
            latitude=12.9716,
            longitude=77.5946,
        )
        self.assertEqual(result["category"], Issue.Category.POTHOLE)
        self.assertEqual(result["severity"], Issue.Severity.HIGH)
        self.assertEqual(result["suggested_department_name"], "Roads Department")
        self.assertGreaterEqual(result["confidence"], 0.85)

    def test_duplicate_detection(self):
        # Create an existing open issue at location
        Issue.objects.create(
            citizen=self.citizen,
            title="Pothole near 5th cross",
            description="Big pothole in middle of street",
            category=Issue.Category.POTHOLE,
            severity=Issue.Severity.MEDIUM,
            status=Issue.Status.REPORTED,
            latitude=12.9716,
            longitude=77.5946,
        )

        # Run AI analysis for nearby report (~15 meters away)
        analysis = CivicAIService.analyze(
            description="Pothole on street",
            latitude=12.9717,
            longitude=77.5947,
        )
        self.assertTrue(analysis["is_duplicate"])
        self.assertIsNotNone(analysis["duplicate_issue_id"])
        self.assertLess(analysis["duplicate_distance_meters"], 50)

    def test_status_workflow_and_notifications(self):
        issue = Issue.objects.create(
            citizen=self.citizen,
            title="Broken streetlight",
            description="Lamp pole is completely dark",
            category=Issue.Category.STREETLIGHT,
            status=Issue.Status.REPORTED,
            department=self.roads_dept,
        )

        # Transition to ASSIGNED
        issue.assigned_maintainer = self.maintainer
        issue.status = Issue.Status.ASSIGNED
        issue.save()
        self.assertEqual(issue.status, Issue.Status.ASSIGNED)

        # Transition to IN_PROGRESS
        issue.status = Issue.Status.IN_PROGRESS
        issue.save()
        self.assertEqual(issue.status, Issue.Status.IN_PROGRESS)

        # Transition to RESOLVED with notes
        issue.status = Issue.Status.RESOLVED
        issue.resolution_notes = "Replaced sodium lamp bulb."
        issue.save()
        self.assertEqual(issue.status, Issue.Status.RESOLVED)

        # Citizen feedback transitions to CLOSED
        issue.feedback_rating = 5
        issue.feedback_comment = "Excellent lighting restoration."
        issue.status = Issue.Status.CLOSED
        issue.save()
        self.assertEqual(issue.status, Issue.Status.CLOSED)
        self.assertEqual(issue.feedback_rating, 5)
