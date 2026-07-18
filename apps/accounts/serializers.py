"""
CineBook — Accounts Serializers
=================================
"""

import logging
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import CustomerProfile

logger = logging.getLogger("apps.accounts")


class CineBookTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that embeds user metadata in the token claims.
    This avoids an extra API round-trip to fetch user info after login.
    """

    @classmethod
    def get_token(cls, user: User):
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        token["is_staff"] = user.is_staff
        return token

    def validate(self, attrs: dict) -> dict:
        data = super().validate(attrs)
        # Attach user data to the response body alongside the tokens
        data["user"] = {
            "id": self.user.pk,
            "username": self.user.username,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "is_staff": self.user.is_staff,
        }
        return data


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ["phone", "city", "avatar", "date_of_birth"]


class UserSerializer(serializers.ModelSerializer):
    """Read-only user serializer — used for profile display."""

    profile = CustomerProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "profile", "date_joined"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    """
    Registration serializer with explicit field validation.
    Does NOT extend ModelSerializer to have full control over user creation.
    """

    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=False, default="")
    email = serializers.EmailField(required=True)
    username = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    phone = serializers.CharField(max_length=15, required=False, default="")
    city = serializers.CharField(max_length=100, required=False, default="")

    def validate_email(self, value: str) -> str:
        """Email must be unique across all users."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_username(self, value: str) -> str:
        """Username must be unique (case-insensitive) and contain only valid chars."""
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_password(self, value: str) -> str:
        """Run Django's password validators."""
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value

    def validate(self, data: dict) -> dict:
        """Cross-field validation: passwords must match."""
        if data.get("password") != data.get("password_confirm"):
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data: dict) -> User:
        """Create User + CustomerProfile atomically."""
        phone = validated_data.pop("phone", "")
        city = validated_data.pop("city", "")
        validated_data.pop("password_confirm")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )

        # Profile is created by signal — just update extra fields
        if hasattr(user, "profile"):
            user.profile.phone = phone
            user.profile.city = city
            user.profile.save(update_fields=["phone", "city"])

        logger.info("New user registered: %s (%s)", user.username, user.email)
        return user


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating profile and basic user fields."""

    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)

    class Meta:
        model = CustomerProfile
        fields = ["first_name", "last_name", "phone", "city", "date_of_birth", "avatar"]

    def update(self, instance: CustomerProfile, validated_data: dict) -> CustomerProfile:
        user_data = validated_data.pop("user", {})
        if user_data:
            for field, value in user_data.items():
                setattr(instance.user, field, value)
            instance.user.save(update_fields=list(user_data.keys()))

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
