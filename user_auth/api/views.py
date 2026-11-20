from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CookieTokenRefreshSerializer,
    LoginSerializer,
    RegistrationSerializer,
)
from .utils import (
    attach_jwt_cookies,
    authenticate_login_data,
    blacklist_refresh_token,
    build_login_payload,
    delete_auth_cookies,
    set_auth_cookie,
)


class RegistrationView(generics.CreateAPIView):
    """Handle registration of new user accounts."""

    serializer_class = RegistrationSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        """Validate registration data and create a new user."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"detail": "User created successfully!"},
            status=status.HTTP_201_CREATED,
        )


class LoginView(generics.GenericAPIView):
    """Authenticate a user and set JWT HTTP-only cookies."""

    serializer_class = LoginSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate credentials and return user info with auth cookies."""
        user = authenticate_login_data(self.get_serializer(data=request.data))
        if user is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        payload = build_login_payload(user)
        response = Response(payload, status=status.HTTP_200_OK)
        attach_jwt_cookies(response, user)
        return response


class LogoutView(APIView):
    """Log out an authenticated user and invalidate refresh tokens."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Blacklist the refresh token and clear all auth cookies."""
        blacklist_refresh_token(request.COOKIES.get("refresh_token"))
        message = (
            "Log-Out successfully! All Tokens will be deleted. "
            "Refresh token is now invalid."
        )
        response = Response({"detail": message}, status=status.HTTP_200_OK)
        delete_auth_cookies(response)
        return response


class CookieTokenRefreshView(generics.GenericAPIView):
    """Refresh the access token using the refresh token cookie."""

    serializer_class = CookieTokenRefreshSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate the refresh cookie and issue a new access cookie."""
        data = {"refresh": request.COOKIES.get("refresh_token")}
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response(
                {"detail": "Refresh token is invalid or missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        access_token = serializer.validated_data["access"]
        payload = {"detail": "Token refreshed"}
        response = Response(payload, status=status.HTTP_200_OK)
        set_auth_cookie(response, "access_token", access_token)
        return response