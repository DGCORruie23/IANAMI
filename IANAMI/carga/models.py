from django.db import models

class Estado(models.Model):
    nombre = models.CharField(max_length=150, unique=True, db_index=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"

class EstadoOR(models.Model):
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT, db_index=True)
    cinturon = models.IntegerField(null=True, blank=True)
    ceco = models.CharField(max_length=100, null=True, blank=True)
    frontera = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.estado.nombre} - OR"

    class Meta:
        verbose_name = "OR y Estado"
        verbose_name_plural = "OR y Estados"


class Nacionalidad(models.Model):
    nombre = models.CharField(max_length=150, unique=True, db_index=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Nacionalidad"
        verbose_name_plural = "Nacionalidades"

class CanalizadoAdulto(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    apellidos = models.CharField(max_length=200, null=True, blank=True)
    nombres = models.CharField(max_length=200, null=True, blank=True)
    sexo = models.CharField(max_length=50, null=True, blank=True)
    motivo_salida = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]
        verbose_name = "Adulto Canalizado"
        verbose_name_plural = "Adultos Canalizados"

class CanalizadoNNA(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    apellidos = models.CharField(max_length=200, null=True, blank=True)
    nombres = models.CharField(max_length=200, null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=50, null=True, blank=True)
    clasificacion = models.CharField(max_length=100, null=True, blank=True)
    motivo_salida = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]
        verbose_name = "NNA Canalizado"
        verbose_name_plural = "NNAs Canalizados"

class CondicionEstancia(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    documentos_migratorios = models.IntegerField(default=0)
    tarjeta_residente_permanente = models.IntegerField(default=0)
    tarjeta_residente_temporal = models.IntegerField(default=0)
    tarjeta_residente_temporal_estudiante = models.IntegerField(default=0)
    tarjeta_visitante_razones_humanitarias = models.IntegerField(default=0)
    tarjeta_visitante_adopcion = models.IntegerField(default=0)
    tarjeta_visitante_regional = models.IntegerField(default=0)
    tarjeta_visitante_trabajador_fronterizo = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]
        verbose_name = "Condicion de Estancia"
        verbose_name_plural = "Condicion de Estancia"

class MotivoEstancia(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    motivo_estancia = models.CharField(max_length=250, null=True, blank=True)
    documentos_migratorios = models.IntegerField(default=0)
    tarjeta_residente_permanente = models.IntegerField(default=0)
    tarjeta_residente_temporal = models.IntegerField(default=0)
    tarjeta_residente_temporal_estudiante = models.IntegerField(default=0)
    tarjeta_visitante_razones_humanitarias = models.IntegerField(default=0)
    tarjeta_visitante_adopcion = models.IntegerField(default=0)
    tarjeta_visitante_regional = models.IntegerField(default=0)
    tarjeta_visitante_trabajador_fronterizo = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]
        verbose_name = "Motivo de Estancia"
        verbose_name_plural = "Motivos de Estancia"

class Encuentro(models.Model):
    fecha = models.DateField(db_index=True)
    encuentro = models.CharField(max_length=100, db_index=True)  # USBP, OFO, CBP ONE
    location = models.CharField(max_length=150, null=True, blank=True)
    ciudad_eeuu = models.CharField(max_length=150, null=True, blank=True)
    ciudad_mx = models.CharField(max_length=150, null=True, blank=True)
    total = models.IntegerField(default=0)
    mexico = models.IntegerField(default=0)
    extranjeros = models.IntegerField(default=0)
    desglose_nacionalidades = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['fecha', 'encuentro']),
        ]
        verbose_name = "Encuentros"
        verbose_name_plural = "Encuentros"

class ExtranjeroRecibido(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)
    adultos = models.IntegerField(default=0)
    menores = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]

class Inadmision(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]
        verbose_name = "Inadmision"
        verbose_name_plural = "Inadmisiones"

class Internacion(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)
    aereo = models.IntegerField(default=0)
    maritimo = models.IntegerField(default=0)
    terrestre = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]
        verbose_name = "Internacion"
        verbose_name_plural = "Internaciones"

class MexicanoRecibido(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)
    adultos = models.IntegerField(default=0)
    menores = models.IntegerField(default=0)
    nna_no_acompanados = models.IntegerField(default=0)
    nna_acompanados = models.IntegerField(default=0)
    terrestres = models.IntegerField(default=0)
    vuelos = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado']),
        ]

class Presentado(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    estacion_migratoria = models.CharField(max_length=250, null=True, blank=True)
    total = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]
        verbose_name = "Presentados"
        verbose_name_plural = "Presentados"

class Rescatado(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)
    primera_vez = models.IntegerField(default=0)
    reincidencia = models.IntegerField(default=0)
    presentados_em = models.IntegerField(default=0)
    canalizados_dif = models.IntegerField(default=0)
    conduccion_norte_sur = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]
        verbose_name = "Rescatado"
        verbose_name_plural = "Rescatados"

class Retornado(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)
    deportados = models.IntegerField(default=0)
    retornos_asistidos = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'nacionalidad']),
        ]

class Traslado(models.Model):
    dia = models.DateField(db_index=True)
    estado_origen = models.ForeignKey(EstadoOR, on_delete=models.PROTECT, related_name='traslados_origen')
    estado_destino = models.ForeignKey(EstadoOR, on_delete=models.PROTECT, related_name='traslados_destino')
    total = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado_origen', 'estado_destino']),
        ]

class Caravana(models.Model):
    dia = models.DateField(db_index=True)
    anio = models.IntegerField(db_index=True)
    estado_partida = models.ForeignKey(EstadoOR, on_delete=models.PROTECT, related_name='caravanas_partida')
    lugar_partida = models.CharField(max_length=250, null=True, blank=True)
    nombre = models.CharField(max_length=200, null=True, blank=True)
    estado_disolucion = models.ForeignKey(EstadoOR, on_delete=models.PROTECT, related_name='caravanas_disolucion', null=True, blank=True)
    lugar_disolucion = models.CharField(max_length=250, null=True, blank=True)
    personas_inicio = models.IntegerField(default=0)
    personas_rescatadas = models.IntegerField(default=0)
    personas_documentadas = models.IntegerField(default=0)
    personas_trasladadas = models.IntegerField(default=0)
    tipo_documento = models.CharField(max_length=250, null=True, blank=True)
    tvrh = models.IntegerField(default=0)
    pam = models.IntegerField(default=0)
    fmm = models.IntegerField(default=0)
    cita_comar = models.IntegerField(default=0)
    docs_provisionales = models.IntegerField(default=0)
    desglose_nacionalidades = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'nombre']),
        ]

class ActasCivil(models.Model):
    fecha_solicitud = models.DateField(db_index=True)
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT, db_index=True)
    oficina = models.CharField(max_length=100, null=True, blank=True)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    nut = models.CharField(max_length=100, null=True, blank=True)
    tipo_tramite = models.CharField(max_length=250, null=True, blank=True)
    tipo_acto = models.CharField(max_length=100, null=True, blank=True)
    no_acta = models.CharField(max_length=100, null=True, blank=True)
    oficialia = models.CharField(max_length=250, null=True, blank=True)
    libro = models.CharField(max_length=100, null=True, blank=True)
    entidad = models.CharField(max_length=50, null=True, blank=True)
    municipio = models.CharField(max_length=100, null=True, blank=True)
    fecha_registro = models.DateField(null=True, blank=True)
    validacion = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.fecha_solicitud}->{self.nacionalidad}--{self.nut}"

    class Meta:
        verbose_name = "Acta Civil"
        verbose_name_plural = "Actas Civiles"

class TramitesMigratorios(models.Model):
    fecha = models.DateField(db_index=True)
    estado = models.ForeignKey(Estado, on_delete=models.PROTECT, db_index=True)
    oficina = models.CharField(max_length=100, null=True, blank=True)
    tramite = models.CharField(max_length=100, null=True, blank=True)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    recibidos = models.IntegerField(default=0)
    concluidos = models.IntegerField(default=0)
    resueltos = models.IntegerField(default=0)
    resueltos_dentro_plazo = models.IntegerField(default=0)
    resueltos_fuera_plazo = models.IntegerField(default=0)
    proceso = models.IntegerField(default=0)
    proceso_dentro_plazo = models.IntegerField(default=0)
    proceso_fuera_plazo = models.IntegerField(default=0)
    

    def __str__(self):
        return f"{self.fecha}->{self.estado}--{self.nacionalidad}"

    class Meta:
        verbose_name = "Tramites Migratorios"
        verbose_name_plural = "Tramites Migratorios"

#
#-----------------------------------------------------------------------------------------------------
#--------------------------------MODELOS para ACTUALIZAR ---------------------------------------------
#-----------------------------------------------------------------------------------------------------
#

class TipoIngresoP(models.Model):
    tipo = models.CharField(max_length=150, unique=True, db_index=True)

    def __str__(self):
        return self.tipo

    class Meta:
        verbose_name = "Tipo de Ingreso"
        verbose_name_plural = "Tipos de Ingreso"

class InternacionN(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    puntoInternacion = models.CharField(max_length=255, null=True, blank=True)
    tipoIngreso = models.ForeignKey(TipoIngresoP, on_delete=models.PROTECT, db_index=True)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'tipoIngreso', 'puntoInternacion', 'nacionalidad']),
        ]
        verbose_name = "Internacion Nuevo"
        verbose_name_plural = "Internaciones N"


class Inadmision2da(models.Model):
    dia = models.DateField(db_index=True)
    estado = models.ForeignKey(EstadoOR, on_delete=models.PROTECT)
    puntoInternacion = models.CharField(max_length=255, null=True, blank=True)
    determinacion = models.CharField(max_length=150, db_index=True)
    nacionalidad = models.ForeignKey(Nacionalidad, on_delete=models.PROTECT)
    total = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['dia', 'estado', 'puntoInternacion', 'determinacion', 'nacionalidad']),
        ]
        verbose_name = "Inadmision 2da Rev"
        verbose_name_plural = "Inadmisiones 2da Rev"


class MetricaComparativa(models.Model):
    categoria = models.CharField(max_length=150, db_index=True)  # Ej. ACCIONES DE CONTROL, RESCATES, REPATRIADOS, PLANTILLA, SISTEMAS
    subcategoria = models.CharField(max_length=150, db_index=True) # Ej. ENCUENTROS, MEX, EXT, TRASLADO_AEREO_PERSONAS, SISTEMAS_LIST
    anio = models.IntegerField(db_index=True)                      # Ej. 2017, 2018, ... 2026
    valor_numero = models.BigIntegerField(null=True, blank=True)   # Conteos / montos
    valor_texto = models.CharField(max_length=255, null=True, blank=True) # Textos cortos (nombres de sistemas, etc)
    datos_json = models.JSONField(null=True, blank=True)          # Listas o diccionarios complejos

    class Meta:
        indexes = [
            models.Index(fields=['categoria', 'subcategoria', 'anio']),
        ]
        verbose_name = "Métrica Comparativa"
        verbose_name_plural = "Métricas Comparativas"