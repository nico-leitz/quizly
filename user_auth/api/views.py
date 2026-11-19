from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .serializers import RegistrationSerializer


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"detail": "User created successfully!"},
            status=status.HTTP_201_CREATED,
        )