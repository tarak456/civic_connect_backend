from rest_framework import serializers
from .models import Issue, Department, Notification


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "recipient", "issue", "title", "message", "notification_type", "is_read", "created_at"]
        read_only_fields = ["id", "recipient", "created_at"]


class IssueSerializer(serializers.ModelSerializer):
    citizen_username = serializers.CharField(source="citizen.username", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    assigned_maintainer_name = serializers.CharField(source="assigned_maintainer.username", read_only=True)

    class Meta:
        model = Issue
        fields = [
            "id", "citizen", "citizen_username", "title", "description", "category", "photo",
            "latitude", "longitude", "address_text", "status", "severity",
            "ai_confidence", "ai_detected_category", "is_possible_duplicate", "duplicate_of",
            "department", "department_name", "assigned_maintainer", "assigned_maintainer_name", "admin_notes",
            "resolution_notes", "resolution_photo", "feedback_rating", "feedback_comment",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "citizen", "citizen_username", "department_name",
            "assigned_maintainer_name", "created_at", "updated_at",
        ]


class IssueCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = [
            "title", "description", "category", "photo",
            "latitude", "longitude", "address_text", "severity",
            "ai_confidence", "ai_detected_category", "is_possible_duplicate", "duplicate_of",
        ]