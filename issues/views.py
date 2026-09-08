from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.models import User
from .models import Issue, Department, Notification
from .serializers import (
    IssueSerializer,
    IssueCreateSerializer,
    DepartmentSerializer,
    NotificationSerializer,
)
from .services.ai_service import CivicAIService


class IsOwnerOrStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in (User.Role.GOVERNMENT, User.Role.MAINTAINER):
            return True
        return obj.citizen_id == user.id


class IssueViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        user = self.request.user
        qs = Issue.objects.select_related("citizen", "department", "assigned_maintainer").all()
        if user.role == User.Role.CITIZEN:
            return qs.filter(citizen=user)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return IssueCreateSerializer
        return IssueSerializer

    def perform_create(self, serializer):
        photo = self.request.FILES.get("photo")
        description = self.request.data.get("description", "")
        latitude = self.request.data.get("latitude")
        longitude = self.request.data.get("longitude")

        try:
            lat = float(latitude) if latitude is not None else None
            lon = float(longitude) if longitude is not None else None
        except (ValueError, TypeError):
            lat, lon = None, None

        ai_res = CivicAIService.analyze(
            image_file=photo,
            description=description,
            latitude=lat,
            longitude=lon,
        )

        # Prepopulate AI values if not explicitly provided
        ai_confidence = self.request.data.get("ai_confidence") or ai_res["confidence"]
        ai_detected_category = self.request.data.get("ai_detected_category") or ai_res["category"]
        severity = self.request.data.get("severity") or ai_res["severity"]
        is_possible_duplicate = ai_res["is_duplicate"]
        duplicate_of_id = ai_res["duplicate_issue_id"]

        # If department is not assigned, route to suggested department
        dept_id = self.request.data.get("department") or ai_res["suggested_department_id"]

        issue = serializer.save(
            citizen=self.request.user,
            severity=severity,
            ai_confidence=ai_confidence,
            ai_detected_category=ai_detected_category,
            is_possible_duplicate=is_possible_duplicate,
            duplicate_of_id=duplicate_of_id,
            department_id=dept_id,
        )

        # Notify Citizen that report was received
        Notification.objects.create(
            recipient=self.request.user,
            issue=issue,
            title="Report Received",
            message=f"Your {issue.get_category_display()} report '{issue.title}' has been submitted and queued for review.",
            notification_type=Notification.NotificationType.STATUS_UPDATE,
        )

    @action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny])
    def ai_analyze(self, request):
        """
        Public/Authenticated AI analysis endpoint for the guided reporting flow.
        """
        photo = request.FILES.get("photo")
        description = request.data.get("description", "")
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")

        try:
            lat = float(latitude) if latitude is not None else None
            lon = float(longitude) if longitude is not None else None
        except (ValueError, TypeError):
            lat, lon = None, None

        result = CivicAIService.analyze(
            image_file=photo,
            description=description,
            latitude=lat,
            longitude=lon,
        )
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def assigned_to_me(self, request):
        issues = Issue.objects.filter(assigned_maintainer=request.user)
        return Response(IssueSerializer(issues, many=True).data)

    @action(detail=False, methods=["get"])
    def city_health(self, request):
        """
        Calculates dynamic city health statistics from actual civic issue data.
        """
        total = Issue.objects.count()
        if total == 0:
            return Response({
                "overall_health": 88,
                "breakdown": {
                    "Roads": 0.85,
                    "Lighting": 0.90,
                    "Sanitation": 0.82,
                    "Drainage": 0.80,
                    "Water Works": 0.88,
                },
                "total_issues": 0,
                "resolved_issues": 0,
            })

        resolved = Issue.objects.filter(status__in=[Issue.Status.RESOLVED, Issue.Status.CLOSED]).count()
        active = total - resolved

        # Baseline city health score
        health_ratio = max(0.40, min(0.98, (resolved + (0.5 * (total - active))) / max(total, 1)))
        overall_health = round(health_ratio * 100)

        categories_map = {
            "Roads": [Issue.Category.POTHOLE, Issue.Category.ROAD_DAMAGE],
            "Lighting": [Issue.Category.STREETLIGHT],
            "Sanitation": [Issue.Category.GARBAGE, Issue.Category.ILLEGAL_DUMPING],
            "Drainage": [Issue.Category.DRAINAGE],
            "Water Works": [Issue.Category.WATER_LEAKAGE],
        }

        breakdown = {}
        for name, cats in categories_map.items():
            cat_total = Issue.objects.filter(category__in=cats).count()
            cat_resolved = Issue.objects.filter(
                category__in=cats, status__in=[Issue.Status.RESOLVED, Issue.Status.CLOSED]
            ).count()
            if cat_total == 0:
                breakdown[name] = 0.85  # Default healthy baseline
            else:
                score = round(max(0.35, min(0.99, (cat_resolved + 1) / (cat_total + 1))), 2)
                breakdown[name] = score

        return Response({
            "overall_health": overall_health,
            "breakdown": breakdown,
            "total_issues": total,
            "resolved_issues": resolved,
        })

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """
        Aggregated metrics for Government Admin Dashboard.
        """
        total = Issue.objects.count()
        reported = Issue.objects.filter(status=Issue.Status.REPORTED).count()
        under_review = Issue.objects.filter(status=Issue.Status.UNDER_REVIEW).count()
        assigned = Issue.objects.filter(status=Issue.Status.ASSIGNED).count()
        in_progress = Issue.objects.filter(status=Issue.Status.IN_PROGRESS).count()
        resolved = Issue.objects.filter(status=Issue.Status.RESOLVED).count()
        closed = Issue.objects.filter(status=Issue.Status.CLOSED).count()

        high_priority = Issue.objects.filter(
            severity=Issue.Severity.HIGH,
            status__in=[
                Issue.Status.REPORTED,
                Issue.Status.UNDER_REVIEW,
                Issue.Status.ASSIGNED,
                Issue.Status.IN_PROGRESS,
            ],
        ).count()

        # Category breakdown
        category_counts = {}
        for code, label in Issue.Category.choices:
            cnt = Issue.objects.filter(category=code).count()
            category_counts[label] = cnt

        # Severity breakdown
        severity_counts = {
            "Low": Issue.objects.filter(severity=Issue.Severity.LOW).count(),
            "Medium": Issue.objects.filter(severity=Issue.Severity.MEDIUM).count(),
            "High": Issue.objects.filter(severity=Issue.Severity.HIGH).count(),
        }

        # Resolution rate
        completed = resolved + closed
        resolution_rate = round((completed / total * 100) if total > 0 else 100.0, 1)

        # Department breakdown
        dept_workload = []
        for dept in Department.objects.all():
            cnt = dept.issues.count()
            resolved_cnt = dept.issues.filter(status__in=[Issue.Status.RESOLVED, Issue.Status.CLOSED]).count()
            dept_workload.append({
                "id": dept.id,
                "name": dept.name,
                "total_issues": cnt,
                "resolved_issues": resolved_cnt,
            })

        return Response({
            "total": total,
            "pending": reported,
            "under_review": under_review,
            "assigned": assigned,
            "in_progress": in_progress,
            "resolved": resolved,
            "closed": closed,
            "high_priority": high_priority,
            "resolution_rate": resolution_rate,
            "category_counts": category_counts,
            "severity_counts": severity_counts,
            "department_workload": dept_workload,
        })

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        if request.user.role != User.Role.GOVERNMENT:
            return Response(
                {"detail": "Only Government Admins can assign issues."},
                status=status.HTTP_403_FORBIDDEN,
            )
        issue = self.get_object()
        department_id = request.data.get("department")
        maintainer_id = request.data.get("assigned_maintainer")
        admin_notes = request.data.get("admin_notes")

        if department_id:
            issue.department_id = department_id
        if maintainer_id:
            issue.assigned_maintainer_id = maintainer_id
            issue.status = Issue.Status.ASSIGNED
        if admin_notes:
            issue.admin_notes = admin_notes
        issue.save()

        # Notify Citizen
        dept_name = issue.department.name if issue.department else "a Municipal Department"
        Notification.objects.create(
            recipient=issue.citizen,
            issue=issue,
            title="Issue Assigned",
            message=f"Your issue '{issue.title}' has been assigned to {dept_name} for remediation.",
            notification_type=Notification.NotificationType.ASSIGNMENT,
        )

        # Notify Maintainer if assigned
        if issue.assigned_maintainer:
            Notification.objects.create(
                recipient=issue.assigned_maintainer,
                issue=issue,
                title="New Task Assigned",
                message=f"You have been assigned to resolve '{issue.title}' in {dept_name}.",
                notification_type=Notification.NotificationType.ASSIGNMENT,
            )

        return Response(IssueSerializer(issue).data)

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):
        issue = self.get_object()
        new_status = request.data.get("status")

        if request.user.role == User.Role.MAINTAINER:
            allowed = {Issue.Status.IN_PROGRESS, Issue.Status.RESOLVED}
        elif request.user.role == User.Role.GOVERNMENT:
            allowed = set(Issue.Status.values)
        else:
            return Response(
                {"detail": "Citizens cannot directly change issue status."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if new_status not in allowed:
            return Response(
                {"detail": f"Status '{new_status}' is not allowed for your role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        issue.status = new_status
        if request.data.get("resolution_notes"):
            issue.resolution_notes = request.data["resolution_notes"]
        if "resolution_photo" in request.FILES:
            issue.resolution_photo = request.FILES["resolution_photo"]
        issue.save()

        # Event-driven Notifications
        if new_status == Issue.Status.IN_PROGRESS:
            Notification.objects.create(
                recipient=issue.citizen,
                issue=issue,
                title="Work In Progress",
                message=f"Field work has begun on your reported issue: '{issue.title}'.",
                notification_type=Notification.NotificationType.STATUS_UPDATE,
            )
        elif new_status == Issue.Status.RESOLVED:
            Notification.objects.create(
                recipient=issue.citizen,
                issue=issue,
                title="Issue Resolved! 🎉",
                message=f"Your report '{issue.title}' has been resolved. Please inspect and leave your feedback.",
                notification_type=Notification.NotificationType.FEEDBACK_REQUEST,
            )
        elif new_status == Issue.Status.UNDER_REVIEW:
            Notification.objects.create(
                recipient=issue.citizen,
                issue=issue,
                title="Under Review",
                message=f"Your report '{issue.title}' is currently under review by municipal authorities.",
                notification_type=Notification.NotificationType.STATUS_UPDATE,
            )

        return Response(IssueSerializer(issue).data)

    @action(detail=True, methods=["post"])
    def feedback(self, request, pk=None):
        issue = self.get_object()
        if issue.citizen_id != request.user.id:
            return Response(
                {"detail": "Only the reporting citizen can leave feedback."},
                status=status.HTTP_403_FORBIDDEN,
            )

        rating = request.data.get("feedback_rating")
        try:
            rating_val = int(rating)
            if rating_val < 1 or rating_val > 5:
                return Response({"detail": "Rating must be between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError):
            return Response({"detail": "Valid numeric rating is required."}, status=status.HTTP_400_BAD_REQUEST)

        issue.feedback_rating = rating_val
        issue.feedback_comment = request.data.get("feedback_comment", "")
        issue.status = Issue.Status.CLOSED
        issue.save()

        # Notify maintainer or admin
        if issue.assigned_maintainer:
            Notification.objects.create(
                recipient=issue.assigned_maintainer,
                issue=issue,
                title="Citizen Feedback Received",
                message=f"Citizen rated your work on '{issue.title}': {rating_val}★.",
                notification_type=Notification.NotificationType.SYSTEM,
            )

        return Response(IssueSerializer(issue).data)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"detail": "Notification marked as read."})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": count})