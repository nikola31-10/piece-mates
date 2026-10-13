from django.contrib import admin
from .models import GameSession, Participant, Challenge, PuzzlePiece

admin.site.register(GameSession)
admin.site.register(Participant)
admin.site.register(Challenge)
admin.site.register(PuzzlePiece)