from django.db import models
from django.contrib.auth.models import User

class Bicicletario(models.Model):
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    external_id = models.CharField(max_length=255, unique=True)  # Para vincular com a API CityBik.es

    def average_rating(self):
        ratings = self.ratings.all()
        if ratings.exists():
            return round(sum(r.value for r in ratings) / ratings.count(), 1)
        return None

class UserBicicletario(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bicicletarios_vinculados')
    bicicletario = models.ForeignKey(Bicicletario, on_delete=models.CASCADE, related_name='vinculos')
    date_added = models.DateTimeField(auto_now_add=True)

class BicicletarioRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bicicletario = models.ForeignKey(Bicicletario, on_delete=models.CASCADE, related_name='ratings')
    value = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'bicicletario')  # Um usuário avalia uma vez
