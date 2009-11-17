from django.db import models

# Create your models here.

class Component(models.Model):
    alias = models.CharField(maxlength=64)
    name = models.CharField(maxlength=512)
    url = models.CharField(maxlength=512)
    permission = models.CharField(maxlength=64,blank=True)
    view_order = models.IntegerField()

    def __str__(self):
        return self.name

    class Admin: 
        pass

