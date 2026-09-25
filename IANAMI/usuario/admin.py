from django.contrib import admin
from .models import Direccion, UsuarioS


@admin.register(Direccion)
class DireccionAdmin(admin.ModelAdmin):
    list_display = ('id', 'abreviatura_dg', 'nombre_dg')
    search_fields = ('nombre_dg', 'abreviatura_dg')
    ordering = ('id',)


@admin.register(UsuarioS)
class UsuarioSAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'nombre', 'apellido', 'area', 'tipo_usuario')
    list_filter = ('tipo', 'area')
    search_fields = (
        'nombre',
        'apellido',
        'user__username',
        'user__email',
        'area__nombre_dg',
        'area__abreviatura_dg'
    )
    ordering = ('id',)

    @admin.display(description="Tipo de Usuario")
    def tipo_usuario(self, obj):
        return obj.get_tipo_display()
