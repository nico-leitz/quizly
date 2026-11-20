from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


def set_auth_cookie(response, key, value):
    """Attach an HTTP-only JWT cookie to the response."""
    response.set_cookie(
        key=key,
        value=value,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="Lax",
    )


def attach_jwt_cookies(response, user):
    """Generate JWT tokens for a user and set them as cookies."""
    refresh = RefreshToken.for_user(user)
    set_auth_cookie(response, "access_token", str(refresh.access_token))
    set_auth_cookie(response, "refresh_token", str(refresh))


def delete_auth_cookies(response):
    """Remove access and refresh token cookies from the response."""
    response.delete_cookie("access_token", path="/", samesite="Lax")
    response.delete_cookie("refresh_token", path="/", samesite="Lax")


def blacklist_refresh_token(refresh_token):
    """Blacklist the provided refresh token if it is valid."""
    if not refresh_token:
        return
    try:
        RefreshToken(refresh_token).blacklist()
    except TokenError:
        pass


def authenticate_login_data(serializer):
    """Validate login data and return the authenticated user or None."""
    if not serializer.is_valid():
        return None
    return authenticate(**serializer.validated_data)


def build_login_payload(user):
    """Build the JSON response body for a successful login."""
    return {
        "detail": "Login successfully!",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        },
    }