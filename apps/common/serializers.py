from rest_framework import serializers


class ChoiceOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()
