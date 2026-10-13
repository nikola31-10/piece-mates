from django import forms
from .models import GameSession, Participant


class GameSessionForm(forms.ModelForm):
    class Meta:
        model = GameSession
        fields = [
            "name",
            "theme",
            "difficulty",
            "objects_per_challenge",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Npr. Friday Team Building"
            }),
            "theme": forms.TextInput(attrs={
                "placeholder": "Npr. Kancelarijski predmeti"
            }),
            "difficulty": forms.Select(choices=[
                ("EASY", "Easy"),
                ("MEDIUM", "Medium"),
                ("HARD", "Hard"),
            ]),
            "objects_per_challenge": forms.Select(choices=[
                (1, "1 predmet"),
                (2, "2 predmeta"),
            ]),
        }


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ["name", "photo"]
        widgets = {
            "photo": forms.ClearableFileInput(
                attrs={"accept": "image/*"}
            )
        }