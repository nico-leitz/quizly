from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class RegistrationSerializer(serializers.ModelSerializer):
    """Validate registration payload and create a new Django user."""

    confirmed_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirmed_password"]
        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True},
        }

    def validate_email(self, value):
        """Ensure the email address is unique (case-insensitive)."""
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value.lower()

    def validate(self, attrs):
        """Ensure password and confirmed_password match."""
        if attrs["password"] != attrs["confirmed_password"]:
            raise serializers.ValidationError(
                {"confirmed_password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        """Create and return a new user with a hashed password."""
        validated_data.pop("confirmed_password")
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer):
    """Validate username and password for user login."""

    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class CookieTokenRefreshSerializer(serializers.Serializer):
    """Validate a refresh token string and generate a new access token."""

    refresh = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Verify the refresh token and return the new access token."""
        try:
            refresh = RefreshToken(attrs["refresh"])
        except TokenError:
            raise serializers.ValidationError(
                "Refresh token is invalid or expired."
            )
        return {"access": str(refresh.access_token)}