import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class GameSession(models.Model):
    STATUS_CHOICES = [
        ("LOBBY", "Lobby"),
        ("GENERATING", "Generating"),
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
    ]

    DIFFICULTY_CHOICES = [
        ("EASY", "Easy"),
        ("MEDIUM", "Medium"),
        ("HARD", "Hard"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(max_length=200)

    # Tema koju organizator definiše
    theme = models.CharField(max_length=200)

    difficulty = models.CharField(
        max_length=20,
        choices=DIFFICULTY_CHOICES,
        default="MEDIUM"
    )

    objects_per_challenge = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(2)
        ]
    )

    # Gemma generisani plan izazova
    ai_plan = models.JSONField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="LOBBY"
    )

    # Unapred pripremljena zajednička fotografija
    final_image = models.ImageField(
        upload_to="final_images/",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total_participants(self):
        return self.participants.count()

    @property
    def unlocked_pieces(self):
        return self.puzzle_pieces.filter(unlocked=True).count()

    @property
    def progress_percentage(self):
        total = self.puzzle_pieces.count()

        if total == 0:
            return 0

        return round(self.unlocked_pieces / total * 100)


class Participant(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="participants"
    )

    name = models.CharField(max_length=100)

    photo = models.ImageField(
        upload_to="participants/"
    )

    # Jedinstveni pristupni token za svakog igrača
    access_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Challenge(models.Model):
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="challenges"
    )

    # Svaki igrač dobija tačno jedan izazov
    participant = models.OneToOneField(
        Participant,
        on_delete=models.CASCADE,
        related_name="challenge"
    )

    # Unapred pripremljena fotografija sa skrivenim predmetima
    image = models.ImageField(
        upload_to="challenges/",
        null=True,
        blank=True
    )

    # Primer:
    # [
    #     {
    #         "name": "stapler",
    #         "x": 0.45,
    #         "y": 0.62
    #     }
    # ]
    hidden_objects = models.JSONField(default=list)

    completed = models.BooleanField(default=False)

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Challenge - {self.participant.name}"


class PuzzlePiece(models.Model):
    session = models.ForeignKey(
        GameSession,
        on_delete=models.CASCADE,
        related_name="puzzle_pieces"
    )

    # Jedan deo puzle po učesniku
    participant = models.OneToOneField(
        Participant,
        on_delete=models.CASCADE,
        related_name="puzzle_piece"
    )

    # Pozicija dela u puzli
    position = models.PositiveIntegerField()

    unlocked = models.BooleanField(default=False)

    unlocked_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["position"]

        constraints = [
            models.UniqueConstraint(
                fields=["session", "position"],
                name="unique_puzzle_position_per_session"
            )
        ]

    def __str__(self):
        return f"Piece {self.position} - {self.participant.name}"