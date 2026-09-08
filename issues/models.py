from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Issue(models.Model):
    class Category(models.TextChoices):
        POTHOLE = "POTHOLE", "Pothole"
        GARBAGE = "GARBAGE", "Garbage / Waste"
        STREETLIGHT = "STREETLIGHT", "Streetlight"
        DRAINAGE = "DRAINAGE", "Drainage"
        WATER_LEAKAGE = "WATER_LEAKAGE", "Water Leakage"
        ROAD_DAMAGE = "ROAD_DAMAGE", "Road Damage"
        ILLEGAL_DUMPING = "ILLEGAL_DUMPING", "Illegal Dumping"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        REPORTED = "REPORTED", "Reported"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    citizen = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reported_issues")
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=Category.choices)
    photo = models.ImageField(upload_to="issue_photos/", blank=True, null=True)

    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    address_text = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REPORTED)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)

    # AI Metadata
    ai_confidence = models.FloatField(blank=True, null=True)
    ai_detected_category = models.CharField(max_length=50, blank=True, null=True)
    is_possible_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey("self", on_delete=models.SET_NULL, blank=True, null=True, related_name="duplicates")

    # Workflow & Assignments
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, blank=True, null=True, related_name="issues")
    assigned_maintainer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name="assigned_issues"
    )
    admin_notes = models.TextField(blank=True, null=True)

    # Resolution
    resolution_notes = models.TextField(blank=True, null=True)
    resolution_photo = models.ImageField(upload_to="resolution_photos/", blank=True, null=True)

    # Citizen Feedback
    feedback_rating = models.PositiveSmallIntegerField(blank=True, null=True)
    feedback_comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        STATUS_UPDATE = "STATUS_UPDATE", "Status Update"
        ASSIGNMENT = "ASSIGNMENT", "Assignment"
        RESOLUTION = "RESOLUTION", "Resolution"
        FEEDBACK_REQUEST = "FEEDBACK_REQUEST", "Feedback Request"
        SYSTEM = "SYSTEM", "System"

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, blank=True, null=True, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=30, choices=NotificationType.choices, default=NotificationType.STATUS_UPDATE
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"To {self.recipient.username}: {self.title} ({'Read' if self.is_read else 'Unread'})"