# =============================================================================
#  Traffic Violation Detection System
#  FILE : backend/api/models.py
#  PHASE: 8 — Database Models
#
#  Defines two tables:
#    1. Vehicle  — every vehicle seen (tracked)
#    2. Violation — confirmed speed violations with plate + evidence image
# =============================================================================

from django.db import models


class Vehicle(models.Model):
    """
    Stores every unique vehicle tracked across video frames.
    One record per track_id per video session.
    """

    track_id    = models.CharField(max_length=20)
    vehicle_type = models.CharField(
        max_length=20,
        choices=[
            ("Car",        "Car"),
            ("Truck",      "Truck"),
            ("Bus",        "Bus"),
            ("Motorcycle", "Motorcycle"),
            ("Vehicle",    "Unknown Vehicle"),
        ],
        default="Vehicle"
    )
    first_seen  = models.DateTimeField(auto_now_add=True)
    last_seen   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-first_seen"]

    def __str__(self):
        return f"{self.vehicle_type} #{self.track_id}"


class Violation(models.Model):
    """
    Stores one record for every confirmed speed violation.

    Fields:
        vehicle_id  → foreign key to Vehicle table
        plate       → OCR-read license plate text
        speed       → calculated speed in km/h
        speed_limit → the limit that was exceeded
        timestamp   → when the violation was detected
        frame_number→ which frame in the video
        image       → saved cropped vehicle image (evidence)
        video_source→ which video file this came from
    """

    vehicle     = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="violations",
        null=True, blank=True
    )
    plate       = models.CharField(max_length=30, default="UNKNOWN")
    speed       = models.FloatField()
    speed_limit = models.IntegerField(default=80)
    timestamp   = models.DateTimeField(auto_now_add=True)
    frame_number = models.IntegerField(default=0)
    image       = models.ImageField(
        upload_to="violations/%Y/%m/%d/",
        null=True, blank=True
    )
    video_source = models.CharField(max_length=255, default="traffic.mp4")

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return (f"Violation — Plate: {self.plate}  "
                f"Speed: {self.speed} km/h  @ {self.timestamp}")

    @property
    def is_violation(self):
        return self.speed > self.speed_limit

    @property
    def overspeed_by(self):
        return round(self.speed - self.speed_limit, 1)
