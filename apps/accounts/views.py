"""
CineBook — Accounts API Views
==============================
"""

import logging
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    CineBookTokenObtainPairSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger("apps.accounts")


class LoginThrottle(AnonRateThrottle):
    """Specific throttle scope for login — 5 attempts per minute."""
    scope = "login"


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/
    Create a new customer account and return JWT tokens.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "validation_error", "message": "Registration failed.",
                 "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()

        # Issue JWT tokens immediately after registration
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Account created successfully.",
                "user": {
                    "id": user.pk,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                },
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Authenticate with email/username + password. Returns JWT pair.
    Rate limited to 5 requests/minute for anonymous users.
    """

    serializer_class = CineBookTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Blacklist the provided refresh token (invalidates the session).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": True, "code": "missing_token", "message": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as exc:
            return Response(
                {"error": True, "code": "invalid_token", "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info("User %s logged out.", request.user.username)
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    """GET /api/v1/auth/profile/ — Retrieve the authenticated user's profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ProfileUpdateView(APIView):
    """PATCH /api/v1/auth/profile/update/ — Update profile fields."""

    permission_classes = [IsAuthenticated]

    def patch(self, request) -> Response:
        profile = request.user.profile
        serializer = ProfileUpdateSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "validation_error", "message": "Update failed.",
                 "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response({"message": "Profile updated.", "profile": serializer.data})
