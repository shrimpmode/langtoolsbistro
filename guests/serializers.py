from rest_framework import serializers

from .models import MockEmail


class LoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class LoginVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)


class MockEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockEmail
        fields = ["id", "to", "subject", "body", "sent_at"]
