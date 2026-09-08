from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role", "employee_id", "phone_number"]

    def validate(self, attrs):
        role = attrs.get("role", User.Role.CITIZEN)
        if role == User.Role.MAINTAINER:
            raise serializers.ValidationError(
                "Maintainer accounts cannot be self-registered. They are created by an existing Maintainer."
            )
        if role == User.Role.GOVERNMENT and not attrs.get("employee_id"):
            raise serializers.ValidationError("employee_id is required for Government Admin signup.")
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        if user.role == User.Role.GOVERNMENT:
            user.is_verified = False
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        if not user.is_verified:
            raise serializers.ValidationError("Account is pending verification by a Maintainer.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "is_verified", "employee_id", "phone_number"]
        read_only_fields = fields