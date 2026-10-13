from django.urls import path
from . import views

urlpatterns = [
    # Organizer
    path(
        "",
        views.create_session,
        name="create_session"
    ),
    path(
        "session/<uuid:session_id>/",
        views.session_detail,
        name="session_detail"
    ),
    path(
        "session/<uuid:session_id>/start/",
        views.start_game,
        name="start_game"
    ),
    path(
        "session/<uuid:session_id>/generate-plan/",
        views.generate_plan,
        name="generate_plan"
    ),
    path(
        "session/<uuid:session_id>/prepare-demo/",
        views.prepare_demo,
        name="prepare_demo"
    ),

    # Participant registration
    path(
        "session/<uuid:session_id>/join/",
        views.join_session,
        name="join_session"
    ),

    # Individual player page
    path(
        "session/<uuid:session_id>/play/<uuid:token>/",
        views.player_session,
        name="player_session"
    ),

    # Check hidden object
    path(
        "session/<uuid:session_id>/play/<uuid:token>/check/",
        views.check_object,
        name="check_object"
    ),

    # Individual player game state
    path(
        "session/<uuid:session_id>/play/<uuid:token>/state/",
        views.player_game_state,
        name="player_game_state"
    ),

    # Organizer game state
    path(
        "session/<uuid:session_id>/state/",
        views.game_state,
        name="game_state"
    ),

    # Lobby participants
    path(
        "session/<uuid:session_id>/participants/",
        views.lobby_participants,
        name="lobby_participants"
    ),
]