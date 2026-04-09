# =============================================================================
#  Traffic Violation Detection System
#  FILE : backend/api/serializers.py
#  PHASE: 9 — REST API Serializers
# =============================================================================

from rest_framework import serializers
from .models import Vehicle, Violation


class VehicleSerializer(serializers.ModelSerializer):
    violation_count = serializers.IntegerField(
        source="violations.count", read_only=True
    )

    class Meta:
        model  = Vehicle
        fields = [
            "id", "track_id", "vehicle_type",
            "first_seen", "last_seen", "violation_count"
        ]


class ViolationSerializer(serializers.ModelSerializer):
    vehicle_type  = serializers.CharField(
        source="vehicle.vehicle_type", read_only=True
    )
    overspeed_by  = serializers.FloatField(read_only=True)
    image_url     = serializers.SerializerMethodField()

    class Meta:
        model  = Violation
        fields = [
            "id", "plate", "speed", "speed_limit",
            "overspeed_by", "timestamp", "frame_number",
            "vehicle_type", "image_url", "video_source"
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None
