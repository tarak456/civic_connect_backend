from rest_framework.routers import DefaultRouter
from .views import IssueViewSet, DepartmentViewSet, NotificationViewSet

router = DefaultRouter()
router.register("issues", IssueViewSet, basename="issue")
router.register("departments", DepartmentViewSet, basename="department")
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = router.urls