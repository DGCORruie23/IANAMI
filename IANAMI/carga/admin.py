from django.contrib import admin
from .models import (
    Estado, EstadoOR, Nacionalidad, CanalizadoAdulto, CanalizadoNNA, CondicionEstancia,
    MotivoEstancia, Encuentro, ExtranjeroRecibido, Inadmision, Internacion,
    MexicanoRecibido, Presentado, Rescatado, Retornado, Traslado, Caravana, ActasCivil,
    TramitesMigratorios
)

@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(EstadoOR)
class EstadoORAdmin(admin.ModelAdmin):
    list_display = ('estado', 'cinturon', 'ceco', 'frontera')
    search_fields = ('estado__nombre', 'ceco')
    list_filter = ('frontera', 'cinturon', 'ceco',)


@admin.register(Nacionalidad)
class NacionalidadAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(CanalizadoAdulto)
class CanalizadoAdultoAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'sexo', 'motivo_salida')
    list_filter = ('estado', 'nacionalidad', 'sexo')
    search_fields = ('apellidos', 'nombres', 'motivo_salida')
    date_hierarchy = 'dia'

@admin.register(CanalizadoNNA)
class CanalizadoNNAAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'clasificacion', 'sexo')
    list_filter = ('estado', 'nacionalidad', 'clasificacion', 'sexo')
    search_fields = ('apellidos', 'nombres', 'clasificacion')
    date_hierarchy = 'dia'

@admin.register(CondicionEstancia)
class CondicionEstanciaAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'documentos_migratorios')
    list_filter = ('estado', 'nacionalidad')
    date_hierarchy = 'dia'

@admin.register(MotivoEstancia)
class MotivoEstanciaAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'motivo_estancia', 'documentos_migratorios')
    list_filter = ('estado', 'nacionalidad', 'motivo_estancia')
    search_fields = ('motivo_estancia',)
    date_hierarchy = 'dia'

@admin.register(Encuentro)
class EncuentroAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'encuentro', 'location', 'ciudad_eeuu', 'ciudad_mx', 'total')
    list_filter = ('encuentro', 'ciudad_eeuu', 'ciudad_mx')
    search_fields = ('location', 'ciudad_eeuu', 'ciudad_mx')
    date_hierarchy = 'fecha'

@admin.register(ExtranjeroRecibido)
class ExtranjeroRecibidoAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'total', 'adultos', 'menores')
    list_filter = ('estado', 'nacionalidad')
    date_hierarchy = 'dia'

@admin.register(Inadmision)
class InadmisionAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'total')
    list_filter = ('estado', 'nacionalidad')
    date_hierarchy = 'dia'

@admin.register(Internacion)
class InternacionAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'total', 'aereo', 'maritimo', 'terrestre')
    list_filter = ('estado', 'nacionalidad')
    date_hierarchy = 'dia'

@admin.register(MexicanoRecibido)
class MexicanoRecibidoAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'total', 'adultos', 'menores', 'terrestres', 'vuelos')
    list_filter = ('estado',)
    date_hierarchy = 'dia'

@admin.register(Presentado)
class PresentadoAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'estacion_migratoria', 'total')
    list_filter = ('estado', 'nacionalidad', 'estacion_migratoria')
    search_fields = ('estacion_migratoria',)
    date_hierarchy = 'dia'

@admin.register(Rescatado)
class RescatadoAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'total', 'primera_vez', 'reincidencia')
    list_filter = ('estado', 'nacionalidad')
    date_hierarchy = 'dia'

@admin.register(Retornado)
class RetornadoAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado', 'nacionalidad', 'total', 'deportados', 'retornos_asistidos')
    list_filter = ('estado', 'nacionalidad')
    date_hierarchy = 'dia'

@admin.register(Traslado)
class TrasladoAdmin(admin.ModelAdmin):
    list_display = ('dia', 'estado_origen', 'estado_destino', 'total')
    list_filter = ('estado_origen', 'estado_destino')
    date_hierarchy = 'dia'

@admin.register(Caravana)
class CaravanaAdmin(admin.ModelAdmin):
    list_display = ('dia', 'anio', 'nombre', 'estado_partida', 'personas_inicio', 'personas_rescatadas')
    list_filter = ('anio', 'estado_partida', 'estado_disolucion')
    search_fields = ('nombre', 'lugar_partida', 'lugar_disolucion')
    date_hierarchy = 'dia'

@admin.register(ActasCivil)
class ActasCivilAdmin(admin.ModelAdmin):
    list_display = ('fecha_solicitud', 'estado', 'oficina', 'nacionalidad', 'nut', 'tipo_tramite', 'tipo_acto', 'no_acta', 'validacion')
    list_filter = ('estado', 'nacionalidad', 'tipo_acto', 'validacion')
    search_fields = ('nut', 'no_acta', 'oficina', 'municipio', 'entidad')
    date_hierarchy = 'fecha_solicitud'

@admin.register(TramitesMigratorios)
class TramitesMigratoriosAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'estado', 'oficina', 'tramite', 'nacionalidad', 'recibidos', 'concluidos', 'resueltos', 'proceso')
    list_filter = ('estado', 'nacionalidad', 'tramite')
    search_fields = ('oficina', 'tramite')
    date_hierarchy = 'fecha'

