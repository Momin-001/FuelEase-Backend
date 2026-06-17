from rest_framework import decorators, generics, permissions, response, views, viewsets

from .serializers import AdminUserSerializer, LoginSerializer, RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login_serializer = LoginSerializer(instance={"user": user})
        return response.Response(login_serializer.data, status=201)


class LoginView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return response.Response(serializer.data)


class MeView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return response.Response(UserSerializer(request.user).data)


class LogoutView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        return response.Response({"detail": "Logged out on client."})


class AdminUserViewSet(viewsets.ModelViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = (permissions.IsAdminUser,)
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.prefetch_related("shops").order_by("-date_joined")

    @decorators.action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        return response.Response(self.get_serializer(user).data)
