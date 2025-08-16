from django.db import models


class CharModel(models.Model):
    field = models.CharField(max_length=10)


class TextModel(models.Model):
    field = models.TextField()


class ForeignKeyModel(models.Model):
    field = models.ForeignKey(CharModel, on_delete=models.CASCADE)


class ManyToManyModel(models.Model):
    field = models.ManyToManyField(CharModel)


class FileModel(models.Model):
    field = models.FileField(upload_to=".")
