from django.db import models
from django.contrib.auth.models import User

types_user = [
    ("1", "Administrador"),
    ("2", "Editor"),
    ("3", "Visualizador"),
]

class Direccion(models.Model):
    nombre_dg = models.CharField(max_length=150, verbose_name="Nombre Dirección General")
    abreviatura_dg = models.CharField(max_length=10, verbose_name="Abreviatura")

    def __str__(self):
        return f"{self.abreviatura_dg} - {self.nombre_dg}"

    class Meta:
        verbose_name = "Dirección General"
        verbose_name_plural = "Direcciones Generales"


class UsuarioS(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil",
        verbose_name="Usuario de Autenticación"
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido = models.CharField(max_length=200, verbose_name="Apellido")
    area = models.ForeignKey(
        Direccion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios",
        verbose_name="Área / Dirección"
    )
    tipo = models.CharField(
        max_length=1,
        choices=types_user,
        default="2",
        verbose_name="Tipo de Usuario"
    )

    def __str__(self):
        area_str = self.area.abreviatura_dg if self.area else "Sin Área"
        return f"{self.nombre} {self.apellido} ({area_str}) - {self.get_tipo_display()}"

    class Meta:
        verbose_name = "Usuario Sistema"
        verbose_name_plural = "Usuarios Sistema"