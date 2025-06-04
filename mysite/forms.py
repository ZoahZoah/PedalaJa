from django import forms
from django.utils.timezone import now
from .models import BicicletarioRating

class SuporteForm(forms.Form):
    nome = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'forms-control', 'placeholder': 'Digite seu nome'}))
    sobrenome = forms.CharField(max_length=10, widget=forms.TextInput(attrs={'class': 'forms-control', 'placeholder': 'Digite seu sobrenome'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'forms-control', 'placeholder': 'Digite seu e-mail'}))
    assunto = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'forms-control', 'placeholder': 'Digite o assunto que deseja falar'}))
    mensagem = forms.CharField(widget=forms.Textarea(attrs={'class': 'forms-control', 'placeholder': 'Digite sua mensagem'}))


class BicicletarioRatingForm(forms.ModelForm):
    class Meta:
        model = BicicletarioRating
        fields = ['value', 'comment']