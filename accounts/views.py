from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        message = (
            "Account created. You can log in now."
            if user.is_verified
            else "Account created. Awaiting verification by a Maintainer."
        )
        return Response({"user": UserSerializer(user).data, "message": message}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PendingGovernmentListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != User.Role.MAINTAINER:
            return User.objects.none()
        return User.objects.filter(role=User.Role.GOVERNMENT, is_verified=False)


class VerifyGovernmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        if request.user.role != User.Role.MAINTAINER:
            return Response({"detail": "Only Maintainers can verify Government accounts."}, status=status.HTTP_403_FORBIDDEN)
        try:
            target = User.objects.get(id=user_id, role=User.Role.GOVERNMENT)
        except User.DoesNotExist:
            return Response({"detail": "Government account not found."}, status=status.HTTP_404_NOT_FOUND)
        target.is_verified = True
        target.save()
        return Response({"detail": f"{target.username} has been verified."})
class MaintainerListView(generics.ListAPIView):
    """Used by Government to pick a maintainer when assigning an issue."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(role=User.Role.MAINTAINER, is_verified=True)