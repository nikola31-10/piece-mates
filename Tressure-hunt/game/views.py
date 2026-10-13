from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.db import transaction
from .models import PuzzlePiece
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
import json
import math

from .models import GameSession, Participant, Challenge
from .forms import GameSessionForm, ParticipantForm
from .services.gemma_service import generate_game_plan
from django.core.files.base import ContentFile
from .services.demo_image_service import prepare_demo_game

def create_session(request):
    if request.method == "POST":
        form = GameSessionForm(request.POST)

        if form.is_valid():
            session = form.save()
            request.session[f"organizer_{session.id}"] = True
            return redirect("session_detail", session_id=session.id)
    else:
        form = GameSessionForm()

    return render(request, "game/create_session.html", {
        "form": form
    })


def session_detail(request, session_id):
    game_session = get_object_or_404(GameSession, id=session_id)

    participant_id = request.session.get(
        f"participant_{game_session.id}"
    )

    my_challenge = None

    if participant_id and game_session.status == "ACTIVE":
        my_challenge = Challenge.objects.filter(
            session=game_session,
            participant_id=participant_id
        ).first()

    return render(request, "game/session_detail.html", {
        "game_session": game_session,
        "participants": game_session.participants.all(),
        "join_url": request.build_absolute_uri(
            reverse("join_session", args=[game_session.id])
        ),
        "is_organizer": request.session.get(
            f"organizer_{game_session.id}", False
        ),
        "my_challenge": my_challenge,
    })

def join_session(request, session_id):
    game_session = get_object_or_404(GameSession, id=session_id)

    if game_session.status != "LOBBY":
        return redirect("session_detail", session_id=session_id)

    if request.method == "POST":
        form = ParticipantForm(request.POST, request.FILES)

        if form.is_valid():
            participant = form.save(commit=False)
            participant.session = game_session
            participant.save()

            return redirect(
                "player_session",
                session_id=game_session.id,
                token=participant.access_token
            )
    else:
        form = ParticipantForm()

    return render(request, "game/join_session.html", {
        "form": form,
        "game_session": game_session,
    })
    
@require_POST
def start_game(request, session_id):
    if not request.session.get(f"organizer_{session_id}", False):
        messages.error(request, "Only the organizer can start the game.")
        return redirect("session_detail", session_id=session_id)

    with transaction.atomic():
        game_session = get_object_or_404(
            GameSession.objects.select_for_update(),
            id=session_id
        )

        if game_session.status != "LOBBY":
            messages.error(request, "Game has already started.")
            return redirect("session_detail", session_id=session_id)

        participants = list(
            game_session.participants.order_by("joined_at", "id")
        )

        if len(participants) < 2:
            messages.error(
                request,
                "At least 2 participants are required."
            )
            return redirect("session_detail", session_id=session_id)

        PuzzlePiece.objects.bulk_create([
            PuzzlePiece(
                session=game_session,
                participant=participant,
                position=index
            )
            for index, participant in enumerate(participants)
        ])

        game_session.status = "GENERATING"
        game_session.save(update_fields=["status"])

    messages.success(
        request,
        "Game started! Preparing AI generation."
    )

    return redirect("session_detail", session_id=session_id)

@require_POST
def generate_plan(request, session_id):
    if not request.session.get(f"organizer_{session_id}", False):
        messages.error(request, "Only the organizer can generate the plan.")
        return redirect("session_detail", session_id=session_id)

    game_session = get_object_or_404(GameSession, id=session_id)

    if game_session.status != "GENERATING" or game_session.ai_plan:
        messages.error(request, "Game plan cannot be generated.")
        return redirect("session_detail", session_id=session_id)

    try:
        plan = generate_game_plan(
            theme=game_session.theme,
            difficulty=game_session.difficulty,
            participant_count=game_session.participants.count(),
            objects_per_challenge=game_session.objects_per_challenge,
        )

        game_session.ai_plan = plan
        game_session.save(update_fields=["ai_plan"])

        messages.success(request, "Gemma generated the game plan!")

    except Exception as e:
        messages.error(request, f"Generation failed: {e}")

    return redirect("session_detail", session_id=session_id)

@require_POST
def prepare_demo(request, session_id):
    if not request.session.get(f"organizer_{session_id}", False):
        messages.error(request, "Only the organizer can start the demo.")
        return redirect("session_detail", session_id=session_id)

    game_session = get_object_or_404(GameSession, id=session_id)

    if game_session.status != "GENERATING":
        messages.error(request, "Invalid game status.")
        return redirect("session_detail", session_id=session_id)

    if game_session.final_image:
        messages.error(request, "Game images are already prepared.")
        return redirect("session_detail", session_id=session_id)

    try:
        count = prepare_demo_game(game_session)

        messages.success(
            request,
            f"Demo ready! Created {count} challenges."
        )

    except Exception as e:
        messages.error(request, f"Demo preparation failed: {e}")

    return redirect("session_detail", session_id=session_id)
@require_POST
def check_object(request, session_id, token):
    participant = get_object_or_404(
        Participant,
        session_id=session_id,
        access_token=token
    )

    try:
        data = json.loads(request.body)
        x = float(data["x"])
        y = float(data["y"])

        if not (
            math.isfinite(x) and math.isfinite(y)
            and 0 <= x <= 1 and 0 <= y <= 1
        ):
            raise ValueError()

    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return JsonResponse(
            {"error": "Invalid coordinates."},
            status=400
        )

    with transaction.atomic():
        game_session = get_object_or_404(
            GameSession.objects.select_for_update(),
            id=session_id
        )

        if game_session.status != "ACTIVE":
            return JsonResponse(
                {"error": "Game is not active."},
                status=400
            )

        challenge = get_object_or_404(
            Challenge.objects.select_for_update(),
            session=game_session,
            participant=participant
        )

        if challenge.completed:
            return JsonResponse({
                "correct": True,
                "completed": True,
                "message": "Challenge already completed."
            })

        objects = list(challenge.hidden_objects)

        for index, obj in enumerate(objects):
            distance = math.sqrt(
                (x - float(obj["x"])) ** 2 +
                (y - float(obj["y"])) ** 2
            )

            if distance <= 0.07:
                found_object = objects.pop(index)

                challenge.hidden_objects = objects

                if not objects:
                    challenge.completed = True
                    challenge.completed_at = timezone.now()

                    piece = get_object_or_404(
                        PuzzlePiece,
                        session=game_session,
                        participant=participant
                    )

                    piece.unlocked = True
                    piece.unlocked_at = timezone.now()
                    piece.save(
                        update_fields=["unlocked", "unlocked_at"]
                    )

                challenge.save()

                if challenge.completed:
                    if not game_session.puzzle_pieces.filter(
                        unlocked=False
                    ).exists():
                        game_session.status = "COMPLETED"
                        game_session.save(update_fields=["status"])

                return JsonResponse({
                    "correct": True,
                    "completed": challenge.completed,
                    "found_object": found_object["name"],
                    "remaining_objects": [
                        obj["name"] for obj in objects
                    ],
                    "message": (
                        "Puzzle piece unlocked!"
                        if challenge.completed
                        else "Object found! Keep searching."
                    )
                })

    return JsonResponse({
        "correct": False,
        "completed": False,
        "message": "Not quite! Try again."
    })

@require_GET
def game_state(request, session_id):
    game_session = get_object_or_404(
        GameSession,
        id=session_id
    )

    participant_id = request.session.get(
        f"participant_{session_id}"
    )

    my_challenge = None

    if participant_id:
        my_challenge = Challenge.objects.filter(
            session=game_session,
            participant_id=participant_id
        ).first()

    pieces = list(
        game_session.puzzle_pieces.values(
            "position", "unlocked"
        ).order_by("position")
    )

    return JsonResponse({
        "status": game_session.status,
        "participant_count": game_session.participants.count(),
        "unlocked_count": sum(
            1 for piece in pieces if piece["unlocked"]
        ),
        "pieces": pieces,
        "my_challenge_completed": (
            my_challenge.completed if my_challenge else False
        ),
        "remaining_objects": (
            [obj["name"] for obj in my_challenge.hidden_objects]
            if my_challenge else []
        )
    })


@require_GET
def lobby_participants(request, session_id):
    game_session = get_object_or_404(
        GameSession,
        id=session_id
    )

    participants = [
        {
            "id": str(participant.id),
            "name": participant.name,
            "photo": participant.photo.url,
        }
        for participant in game_session.participants.all()
    ]

    return JsonResponse({
        "participants": participants,
        "status": game_session.status
    })
def player_session(request, session_id, token):
    game_session = get_object_or_404(
        GameSession,
        id=session_id
    )

    participant = get_object_or_404(
        Participant,
        session=game_session,
        access_token=token
    )

    my_challenge = None

    if game_session.status == "ACTIVE":
        my_challenge = Challenge.objects.filter(
            session=game_session,
            participant=participant
        ).first()

    return render(request, "game/session_detail.html", {
        "game_session": game_session,
        "participants": game_session.participants.all(),
        "is_organizer": False,
        "my_challenge": my_challenge,
        "current_participant": participant,
    })
@require_GET
def player_game_state(request, session_id, token):
    participant = get_object_or_404(
        Participant,
        session_id=session_id,
        access_token=token
    )

    game_session = participant.session

    challenge = Challenge.objects.filter(
        session=game_session,
        participant=participant
    ).first()

    pieces = list(
        game_session.puzzle_pieces.values(
            "position", "unlocked"
        ).order_by("position")
    )

    return JsonResponse({
        "status": game_session.status,
        "participant_count": game_session.participants.count(),
        "unlocked_count": sum(
            1 for piece in pieces if piece["unlocked"]
        ),
        "pieces": pieces,
        "my_challenge_completed": (
            challenge.completed if challenge else False
        ),
        "remaining_objects": (
            [obj["name"] for obj in challenge.hidden_objects]
            if challenge else []
        )
    })
@ensure_csrf_cookie
def player_session(request, session_id, token):
    game_session = get_object_or_404(
        GameSession,
        id=session_id
    )

    participant = get_object_or_404(
        Participant,
        session=game_session,
        access_token=token
    )

    my_challenge = None

    if game_session.status in ["ACTIVE", "COMPLETED"]:
        my_challenge = Challenge.objects.filter(
            session=game_session,
            participant=participant
        ).first()

    return render(request, "game/session_detail.html", {
        "game_session": game_session,
        "participants": game_session.participants.all(),
        "is_organizer": False,
        "my_challenge": my_challenge,
        "current_participant": participant,
    })