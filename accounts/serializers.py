from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import AccessToken

from shops.models import ShopProfile


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "name", "email", "role", "phone", "is_active")


class ShopInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopProfile
        fields = (
            "id", "name", "shop_type", "status", "address", "phone",
            "document_url", "image", "latitude", "longitude",
            "open_time", "close_time",
        )


class AdminUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    shops = ShopInlineSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "name", "email", "role", "phone",
            "is_active", "date_joined", "shops",
        )


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=(
            User.Roles.CUSTOMER,
            User.Roles.MECHANIC_OWNER,
            User.Roles.PETROL_OWNER,
        ),
        default=User.Roles.CUSTOMER,
    )

    class Meta:
        model = User
        fields = ("id", "name", "email", "phone", "role", "password")

    def create(self, validated_data):
        name = validated_data.pop("name")
        password = validated_data.pop("password")
        email = validated_data.pop("email").lower()
        first_name, _, last_name = name.partition(" ")
        user = User(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            **validated_data,
        )
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower()
        password = attrs["password"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("Invalid email or password.") from exc

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is disabled.")

        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        user = instance["user"]
        return {
            "access": str(AccessToken.for_user(user)),
            "user": UserSerializer(user).data,
        }
