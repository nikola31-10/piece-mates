import json
import shutil
from pathlib import Path

from django.conf import settings
from django.core.files import File

from game.models import Challenge


def prepare_demo_game(game_session):
    theme_folder = Path(settings.BASE_DIR) / "demo_assets" / "office"

    manifest_path = theme_folder / "manifest.json"
    group_path = theme_folder / "group.png"

    if not manifest_path.is_file() or not group_path.is_file():
        raise ValueError("Demo assets are missing.")

    with open(manifest_path, encoding="utf-8") as file:
        manifest = json.load(file)

    participants = list(
        game_session.participants.order_by("joined_at", "id")
    )

    definitions = manifest["challenges"]

    if len(definitions) < len(participants):
        raise ValueError(
            "Not enough demo challenges for all participants."
        )

    # Validate all assets before modifying the database.
    for definition in definitions[:len(participants)]:
        image_path = theme_folder / definition["image"]

        if not image_path.is_file():
            raise ValueError(f"Missing image: {image_path.name}")

        if len(definition["objects"]) != game_session.objects_per_challenge:
            raise ValueError(
                "Object count does not match session configuration."
            )

    # Save group photograph.
    with group_path.open("rb") as image_file:
        game_session.final_image.save(
            f"group_{game_session.id}.png",
            File(image_file),
            save=True
        )

    # Save individual challenges.
    for participant, definition in zip(participants, definitions):
        challenge, _ = Challenge.objects.get_or_create(
            participant=participant,
            defaults={"session": game_session}
        )

        challenge.hidden_objects = definition["objects"]
        challenge.completed = False

        image_path = theme_folder / definition["image"]

        with image_path.open("rb") as image_file:
            challenge.image.save(
                f"{game_session.id}_{participant.id}.png",
                File(image_file),
                save=False
            )

        challenge.save()

    # Keep the game plan consistent with the actual images.
    game_session.ai_plan = {
        "challenges": [
            {
                "objects": [
                    obj["name"] for obj in definition["objects"]
                ],
                "hint": definition.get("hint", "")
            }
            for definition in definitions[:len(participants)]
        ]
    }

    game_session.status = "ACTIVE"
    game_session.save(update_fields=["ai_plan", "status"])

    return len(participants)