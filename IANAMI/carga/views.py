import csv
import io
import unicodedata
import json
import pandas as pd
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import (
    Estado, EstadoOR, Nacionalidad, CanalizadoAdulto, CanalizadoNNA, CondicionEstancia,
    MotivoEstancia, Encuentro, ExtranjeroRecibido, Inadmision, Internacion,
    MexicanoRecibido, Presentado, Rescatado, Retornado, Traslado, Caravana, ActasCivil,
    TramitesMigratorios, Inadmision2da, InternacionN, TipoIngresoP, MetricaComparativa,
    MexRepatriados, RepatriadosComerciales
)

# Cache dictionaries for fast queries
estados_cache = {}
nacs_cache = {}

def clean_text(text):
    if not text:
        return ""
    # Normalize unicode characters to decompose them (remove accents)
    nfkd_form = unicodedata.normalize('NFKD', str(text))
    # Filter out the combining diacritical marks
    unaccented = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Convert to uppercase and strip whitespace
    return unaccented.upper().strip()

def preload_nationalities():
    excel_path = "/Users/dgcor/Documents/DOCKER PROJ/comisionado/ianami-datos/Nacionalidades-Paises.xlsx"
    try:
        df = pd.read_excel(excel_path, header=None)
        names = []
        for col in df.columns:
            names.extend(df[col].dropna().astype(str).tolist())
            
        nacs_to_create = []
        existing_nacs = set(Nacionalidad.objects.values_list('nombre', flat=True))
        
        for name in names:
            clean_name = clean_text(name)
            if clean_name and clean_name not in existing_nacs:
                nacs_to_create.append(Nacionalidad(nombre=clean_name))
                existing_nacs.add(clean_name)
                
        if nacs_to_create:
            Nacionalidad.objects.bulk_create(nacs_to_create)
            print(f"[preload] Cargadas {len(nacs_to_create)} nacionalidades desde el Excel.")
    except Exception as e:
        print("[preload] Error cargando nacionalidades desde Excel:", e)

tipos_ingreso_cache = {}

def init_caches():
    global estados_cache, nacs_cache, tipos_ingreso_cache
    estados_cache = {e.estado.nombre.upper().strip(): e for e in EstadoOR.objects.select_related('estado').all()}
    nacs_cache = {n.nombre.upper().strip(): n for n in Nacionalidad.objects.all()}
    tipos_ingreso_cache = {t.tipo.upper().strip(): t for t in TipoIngresoP.objects.all()}

def clean_state_name(nombre):
    if not nombre:
        return ""
    val_str = str(nombre).strip().upper()
    prefixes = ["O.R. ", "OR ", "O.R."]
    for p in prefixes:
        if val_str.startswith(p):
            val_str = val_str[len(p):].strip()
    return clean_text(val_str)

def get_existing_estado(nombre):
    nombre_clean = clean_state_name(nombre)
    if not nombre_clean:
        return None
    if nombre_clean in estados_cache:
        return estados_cache[nombre_clean]
    try:
        est = Estado.objects.get(nombre=nombre_clean)
        estado_or, _ = EstadoOR.objects.get_or_create(estado=est)
        estados_cache[nombre_clean] = estado_or
        return estado_or
    except Estado.DoesNotExist:
        return None

def get_or_create_estado(nombre):
    nombre_clean = clean_state_name(nombre)
    if not nombre_clean:
        nombre_clean = "DESCONOCIDO"
    if nombre_clean not in estados_cache:
        est, _ = Estado.objects.get_or_create(nombre=nombre_clean)
        estado_or, _ = EstadoOR.objects.get_or_create(estado=est)
        estados_cache[nombre_clean] = estado_or
    return estados_cache[nombre_clean]


def get_or_create_nacionalidad(nombre):
    nombre_clean = clean_text(nombre)
    if not nombre_clean:
        nombre_clean = "DESCONOCIDA"
    if nombre_clean not in nacs_cache:
        # Fallback to create if not found, to avoid losing data, but in clean format
        nac, _ = Nacionalidad.objects.get_or_create(nombre=nombre_clean)
        nacs_cache[nombre_clean] = nac
    return nacs_cache[nombre_clean]

def get_or_create_tipo_ingreso(nombre):
    nombre_clean = clean_text(nombre)
    if not nombre_clean:
        nombre_clean = "DESCONOCIDO"
    nombre_clean = nombre_clean[:150]
    if nombre_clean not in tipos_ingreso_cache:
        tipo_obj, _ = TipoIngresoP.objects.get_or_create(tipo=nombre_clean)
        tipos_ingreso_cache[nombre_clean] = tipo_obj
    return tipos_ingreso_cache[nombre_clean]

def parse_date(date_str, dayfirst=False):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    if ' ' in date_str:
        date_str = date_str.split(' ')[0]
    # Check if value is Excel serial number (numeric digit string)
    if date_str.isdigit():
        try:
            val_num = int(date_str)
            if val_num > 1000:
                return pd.to_datetime(val_num, unit='D', origin='1899-12-30').date()
        except Exception:
            pass
    try:
        return pd.to_datetime(date_str, dayfirst=dayfirst).date()
    except Exception:
        pass
    fmts = ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d') if dayfirst else ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y', '%Y/%m/%d')
    for fmt in fmts:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

def parse_int(val):
    if not val:
        return 0
    val_clean = val.strip().replace(',', '').replace(' ', '')
    if val_clean in ('-', '', 'null', 'None'):
        return 0
    try:
        return int(val_clean)
    except ValueError:
        return 0

def process_row_to_batch(model_type, row, batch):
    rows_added = 0
    if model_type == "canalizados_adultos":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        obj = CanalizadoAdulto(
            dia=dia, estado=estado, nacionalidad=nac,
            apellidos=clean_text(row.get("APELLIDO (S)")),
            nombres=clean_text(row.get("NOMBRE (S)")),
            sexo=clean_text(row.get("SEXO")),
            motivo_salida=clean_text(row.get("MOTIVO DE SALIDA"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "canalizados_nna":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        nac_date = parse_date(row.get("FECHA DE NACIMIENTO"))
        obj = CanalizadoNNA(
            dia=dia, estado=estado, nacionalidad=nac,
            apellidos=clean_text(row.get("APELLIDO (S)")),
            nombres=clean_text(row.get("NOMBRE (S)")),
            fecha_nacimiento=nac_date,
            sexo=clean_text(row.get("SEXO")),
            clasificacion=clean_text(row.get("CLASIFICACIÓN")),
            motivo_salida=clean_text(row.get("MOTIVO DE SALIDA"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "condicion_estancia":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        obj = CondicionEstancia(
            dia=dia, estado=estado, nacionalidad=nac,
            documentos_migratorios=parse_int(row.get("Documentos Migratorios")),
            tarjeta_residente_permanente=parse_int(row.get("Tarjeta de Residente Permanente")),
            tarjeta_residente_temporal=parse_int(row.get("Tarjeta de Residente Temporal")),
            tarjeta_residente_temporal_estudiante=parse_int(row.get("Tarjeta de Residente Temporal Estudiante")),
            tarjeta_visitante_razones_humanitarias=parse_int(row.get("Tarjeta de Visitante por razones humanitarias")),
            tarjeta_visitante_adopcion=parse_int(row.get("Tarjeta de Visitante con fines de adopción")),
            tarjeta_visitante_regional=parse_int(row.get("Tarjeta de Visitante Regional")),
            tarjeta_visitante_trabajador_fronterizo=parse_int(row.get("Tarjeta de Visitante Trabajador Fronterizo"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "motivo_estancia":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        obj = MotivoEstancia(
            dia=dia, estado=estado, nacionalidad=nac,
            motivo_estancia=clean_text(row.get("Motivo de Estancia")),
            documentos_migratorios=parse_int(row.get("Documentos Migratorios")),
            tarjeta_residente_permanente=parse_int(row.get("Tarjeta de Residente Permanente")),
            tarjeta_residente_temporal=parse_int(row.get("Tarjeta de Residente Temporal")),
            tarjeta_residente_temporal_estudiante=parse_int(row.get("Tarjeta de Residente Temporal Estudiante")),
            tarjeta_visitante_razones_humanitarias=parse_int(row.get("Tarjeta de Visitante por razones humanitarias")),
            tarjeta_visitante_adopcion=parse_int(row.get("Tarjeta de Visitante con fines de adopción")),
            tarjeta_visitante_regional=parse_int(row.get("Tarjeta de Visitante Regional")),
            tarjeta_visitante_trabajador_fronterizo=parse_int(row.get("Tarjeta de Visitante Trabajador Fronterizo"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "encuentros":
        fecha = parse_date(row.get("FECHA"))
        if not fecha:
            return 0
        struct_keys = {"FECHA", "Encuentro", "Location", "Ciudad EEUU", "Ciudad MX", "TOTAL", "Mexico", "Extranjeros"}
        desglose = {}
        for k, v in row.items():
            if k not in struct_keys and parse_int(v) > 0:
                clean_k = clean_text(k)
                desglose[clean_k] = parse_int(v)
        obj = Encuentro(
            fecha=fecha, encuentro=clean_text(row.get("Encuentro")),
            location=clean_text(row.get("Location")),
            ciudad_eeuu=clean_text(row.get("Ciudad EEUU")),
            ciudad_mx=clean_text(row.get("Ciudad MX")),
            total=parse_int(row.get("TOTAL")),
            mexico=parse_int(row.get("Mexico")), extranjeros=parse_int(row.get("Extranjeros")),
            desglose_nacionalidades=desglose
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "extranjeros_recibidos":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        obj = ExtranjeroRecibido(
            dia=dia, estado=estado, nacionalidad=nac,
            total=parse_int(row.get("EXTRANJEROS RECIBIDOS DE EE.UU.")),
            adultos=parse_int(row.get("ADULTOS")), menores=parse_int(row.get("MENORES"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "inadmisiones":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        obj = Inadmision(
            dia=dia, estado=estado, nacionalidad=nac,
            total=parse_int(row.get("INADMITIDOS"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "internaciones":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        obj = Internacion(
            dia=dia, estado=estado, nacionalidad=nac,
            total=parse_int(row.get("TOTAL DE INGRESOS")),
            aereo=parse_int(row.get("INGRESOS AÉREOS")),
            maritimo=parse_int(row.get("INGRESOS MARÍTIMOS")),
            terrestre=parse_int(row.get("INGRESOS TERRESTRES"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "mexicanos_recibidos":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        obj = MexicanoRecibido(
            dia=dia, estado=estado,
            total=parse_int(row.get("MEXICANOS REPATRIADOS")),
            adultos=parse_int(row.get("ADULTOS")), menores=parse_int(row.get("MENORES")),
            nna_no_acompanados=parse_int(row.get("NNA NO ACOMPAÑADOS")),
            nna_acompanados=parse_int(row.get("NNA ACOMPAÑADOS")),
            terrestres=parse_int(row.get("TERRESTRES")), vuelos=parse_int(row.get("VUELOS PRIM"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "presentados":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        obj = Presentado(
            dia=dia, estado=estado, nacionalidad=nac,
            estacion_migratoria=clean_text(row.get("ESTACIÓN O ESTANCIA MIGRATORIA")),
            total=parse_int(row.get("PRESENTADOS"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "rescatados":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        obj = Rescatado(
            dia=dia, estado=estado, nacionalidad=nac,
            total=parse_int(row.get("EXTRANJEROS RESCATADOS POR EL INM")),
            primera_vez=parse_int(row.get("PRIMERA VEZ")),
            reincidencia=parse_int(row.get("REINCIDENCIA")),
            presentados_em=parse_int(row.get("PRESENTADOS EN EM")),
            canalizados_dif=parse_int(row.get("CANALIZADOS AL DIF")),
            conduccion_norte_sur=parse_int(row.get("CONDUCCIÓN DE NORTE A SUR"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "retornados":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("ESTADO / O.R."))
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD"))
        obj = Retornado(
            dia=dia, estado=estado, nacionalidad=nac,
            total=parse_int(row.get("RETORNADOS A SU PAÍS")),
            deportados=parse_int(row.get("DEPORTADOS")),
            retornos_asistidos=parse_int(row.get("RETORNOS ASISTIDOS"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "traslados":
        dia = parse_date(row.get("DIA"))
        if not dia:
            return 0
        dest_states = ["Baja California", "Sonora", "Chihuahua", "Coahuila", "Nuevo León", "Tamaulipas"]
        for dest in dest_states:
            val = parse_int(row.get(dest))
            if val > 0:
                estado_orig = get_or_create_estado("CHIAPAS")
                estado_dest = get_or_create_estado(dest)
                obj = Traslado(dia=dia, estado_origen=estado_orig, estado_destino=estado_dest, total=val)
                batch.append(obj)
                rows_added += 1
    elif model_type == "caravanas":
        dia = parse_date(row.get("DIA") or row.get("Fecha"))
        if not dia:
            return 0
        est_partida = get_or_create_estado(row.get("Estado de Partida") or row.get("Lugar de partida"))
        est_disol = get_or_create_estado(row.get("Estado de Disolución")) if row.get("Estado de Disolución") else None
        struct_keys = {
            "Año", "DIA", "Fecha", "Estado de Partida", "Lugar de Partida", "Lugar de partida",
            "Nombre de la Caravana", "Estado de Disolución", "Lugar de Disolución",
            "Personas que Aproximadamente Incian la movilización", "Personas Rescatadas",
            "Personas Documentadas", "Personas Trasladadas a Oficinas distintas al origen",
            "Tipo de Documento o Procedimiento", "TVRH", "PAM", "FMM", "CITA COMAR",
            "Documentos Provisionales y Oficios de Salida"
        }
        desglose = {}
        for k, v in row.items():
            if k not in struct_keys and parse_int(v) > 0:
                clean_k = clean_text(k)
                desglose[clean_k] = parse_int(v)
        obj = Caravana(
            dia=dia, anio=parse_int(row.get("Año") or str(dia.year)),
            estado_partida=est_partida,
            lugar_partida=clean_text(row.get("Lugar de Partida") or row.get("Lugar de partida")),
            nombre=clean_text(row.get("Nombre de la Caravana")),
            estado_disolucion=est_disol,
            lugar_disolucion=clean_text(row.get("Lugar de Disolución")),
            personas_inicio=parse_int(row.get("Personas que Aproximadamente Incian la movilización")),
            personas_rescatadas=parse_int(row.get("Personas Rescatadas")),
            personas_documentadas=parse_int(row.get("Personas Documentadas")),
            personas_trasladadas=parse_int(row.get("Personas Trasladadas a Oficinas distintas al origen")),
            tipo_documento=clean_text(row.get("Tipo de Documento o Procedimiento")),
            tvrh=parse_int(row.get("TVRH")), pam=parse_int(row.get("PAM")),
            fmm=parse_int(row.get("FMM")), cita_comar=parse_int(row.get("CITA COMAR")),
            docs_provisionales=parse_int(row.get("Documentos Provisionales y Oficios de Salida")),
            desglose_nacionalidades=desglose
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "actas_civil":
        fecha_sol = parse_date(row.get("FECHA DE SOLICITUD"))
        if not fecha_sol:
            return 0
        est_val = get_existing_estado(row.get("OFICINA DE REPRESENTACIÓN"))
        if not est_val or not est_val.estado:
            return 0
        estado_instance = est_val.estado
        nac = get_or_create_nacionalidad(row.get("NACIONALIDAD DE LA (S) PERSONA (S) PROMOVENTE (S)"))
        fecha_reg = parse_date(row.get("FECHA DE REGISTRO"))
        
        obj = ActasCivil(
            fecha_solicitud=fecha_sol,
            estado=estado_instance,
            oficina=clean_text(row.get("OR SOLICITANTE DE VALIDACIONES"))[:100],
            nacionalidad=nac,
            nut=clean_text(row.get("NUT (S) RELACIONADO (S)"))[:100],
            tipo_tramite=clean_text(row.get("TIPO DE TRÁMITE MIGRATORIO"))[:250],
            tipo_acto=clean_text(row.get("TIPO DE ACTO REGISTRAL"))[:100],
            no_acta=clean_text(row.get("NO. DE ACTA"))[:100],
            oficialia=clean_text(row.get("OFICIALÍA/JUZGADO"))[:250],
            libro=clean_text(row.get("LIBRO"))[:100],
            entidad=clean_text(row.get("ENTIDAD FEDERATIVA DE REGISTRO"))[:50],
            municipio=clean_text(row.get("MUNICIPIO/ALCALDÍA DE REGISTRO"))[:100],
            fecha_registro=fecha_reg,
            validacion=clean_text(row.get("RESULTADO DE LA VALIDACIÓN"))[:100]
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "tramites_migratorios":
        fecha = parse_date(row.get("Fecha"))
        if not fecha:
            return 0
        est_val = get_existing_estado(row.get("Entidad Federativa"))
        if not est_val or not est_val.estado:
            return 0
        estado_instance = est_val.estado
        nac = get_or_create_nacionalidad(row.get("País / Empleador"))
        
        obj = TramitesMigratorios(
            fecha=fecha,
            estado=estado_instance,
            oficina=clean_text(row.get("Oficina"))[:100],
            tramite=clean_text(row.get("Trámite"))[:100],
            nacionalidad=nac,
            recibidos=parse_int(row.get("Recibidos")),
            concluidos=parse_int(row.get("Concluidos")),
            resueltos=parse_int(row.get("Resueltos")),
            resueltos_dentro_plazo=parse_int(row.get("Resueltos dentro del plazo")),
            resueltos_fuera_plazo=parse_int(row.get("Resueltos fuera del plazo")),
            proceso=parse_int(row.get("En proceso")),
            proceso_dentro_plazo=parse_int(row.get("En proceso dentro del plazo")),
            proceso_fuera_plazo=parse_int(row.get("En proceso fuera del plazo"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "inadmisiones2da":
        dia = parse_date(row.get("DIA") or row.get("Dia") or row.get("dia"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("O.R.") or row.get("OR") or row.get("ESTADO / O.R."))
        punto = clean_text(row.get("PUNTO DE INTERNACIÓN") or row.get("PUNTO DE INTERNACION") or row.get("Punto de internacion") or "")[:250]
        det = clean_text(row.get("DETERMINACION") or row.get("DETERMINACIÓN") or row.get("Determinación") or "")[:150]
        nac_val = row.get("NACIONADLIDAD") or row.get("NACIONALIDAD") or row.get("Nacionalidad")
        nac = get_or_create_nacionalidad(nac_val)
        tot = parse_int(row.get("TOTAL") or row.get("Total") or row.get("total"))

        obj = Inadmision2da(
            dia=dia,
            estado=estado,
            puntoInternacion=punto,
            determinacion=det,
            nacionalidad=nac,
            total=tot
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "internaciones_n":
        dia = parse_date(row.get("Dia") or row.get("DIA") or row.get("dia"))
        if not dia:
            return 0
        estado = get_or_create_estado(row.get("O.R.") or row.get("OR") or row.get("ESTADO / O.R."))
        punto = clean_text(row.get("Punto de internacion") or row.get("PUNTO DE INTERNACION") or row.get("PUNTO DE INTERNACIÓN") or "")[:250]
        
        tipo_raw = row.get("Tipo ") or row.get("Tipo") or row.get("TIPO") or row.get("TIPO DE INGRESO") or row.get("Tipo de Ingreso")
        tipo_obj = get_or_create_tipo_ingreso(tipo_raw)
        
        nac = get_or_create_nacionalidad(row.get("Nacionalidad") or row.get("NACIONALIDAD") or row.get("NACIONADLIDAD"))
        tot = parse_int(row.get("Total") or row.get("TOTAL") or row.get("total"))

        obj = InternacionN(
            dia=dia,
            estado=estado,
            puntoInternacion=punto,
            tipoIngreso=tipo_obj,
            nacionalidad=nac,
            total=tot
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "mex_repatriados":
        fecha = parse_date(row.get("FECHA_REPATRIACION") or row.get("FECHA") or row.get("fecha"), dayfirst=True)
        if not fecha:
            return 0
        oficina = clean_text(row.get("ESTADO") or row.get("OFICINA") or row.get("estado") or "")[:100]
        punto = clean_text(row.get("PUNTO_REPATRIACION") or row.get("PUNTO REPATRIACION") or row.get("punto_repatriacion") or "")[:150]
        
        obj = MexRepatriados(
            fecha=fecha,
            oficina=oficina,
            puntoInternación=punto,
            total=parse_int(row.get("MEXICANOS REPATRIADOS") or row.get("TOTAL")),
            hombresA=parse_int(row.get("ADULTOS HOMBRES") or row.get("HOMBRES ADULTOS")),
            mujeresA=parse_int(row.get("ADULTOS MUJERES") or row.get("MUJERES ADULTAS")),
            ninos=parse_int(row.get("MENORES HOMBRES") or row.get("NINOS")),
            ninas=parse_int(row.get("MENORES MUJERES") or row.get("NINAS")),
            acompañados=parse_int(row.get("ACOMPAÑADOS") or row.get("ACOMPANADOS")),
            solos=parse_int(row.get("NO_ACOMPAÑADOS") or row.get("NO ACOMPAÑADOS") or row.get("SOLOS"))
        )
        batch.append(obj)
        rows_added += 1
    elif model_type == "repatriados_comerciales":
        fecha = parse_date(row.get("DIA") or row.get("Dia") or row.get("FECHA") or row.get("fecha"), dayfirst=True)
        if not fecha:
            return 0
        oficina = clean_text(row.get("O.R.") or row.get("OR") or row.get("ESTADO") or row.get("OFICINA") or "")[:100]
        punto = clean_text(row.get("Punto Internacion") or row.get("PUNTO DE INTERNACION") or row.get("PUNTO INTERNACION") or "")[:150]
        
        obj = RepatriadosComerciales(
            fecha=fecha,
            oficina=oficina,
            puntoInternación=punto,
            total=parse_int(row.get("MEXICANOS REPATRIADOS") or row.get("TOTAL")),
            adultos=parse_int(row.get("ADULTOS")),
            menores=parse_int(row.get("MENORES")),
            nna_solos=parse_int(row.get("NNA NO ACOMPAÑADOS") or row.get("NNA NO ACOMPANADOS")),
            nna_acompañados=parse_int(row.get("NNA ACOMPAÑADOS") or row.get("NNA ACOMPANADOS"))
        )
        batch.append(obj)
        rows_added += 1
    return rows_added

@login_required
def upload_view(request):
    if request.method == "POST":
        import json
        is_json = request.content_type == "application/json"
        
        if is_json:
            try:
                data = json.loads(request.body)
            except Exception as e:
                return JsonResponse({"status": "error", "message": f"JSON inválido: {str(e)}"}, status=400)
            model_type = data.get("model_type")
            rows = data.get("rows", [])
        else:
            csv_file = request.FILES.get("file")
            model_type = request.POST.get("model_type")
            
            if not csv_file or not model_type:
                return JsonResponse({"status": "error", "message": "Archivo o tipo de modelo faltante."}, status=400)
        
        # Handle nationalities catalog separately
        if model_type == "nacionalidades":
            try:
                if is_json:
                    names = []
                    for row in rows:
                        if isinstance(row, dict):
                            names.extend([str(v) for v in row.values() if v])
                        elif isinstance(row, str):
                            names.append(row)
                else:
                    df = pd.read_excel(csv_file, header=None)
                    names = []
                    for col in df.columns:
                        names.extend(df[col].dropna().astype(str).tolist())
                    
                nacs_to_create = []
                existing_nacs = set(Nacionalidad.objects.values_list('nombre', flat=True))
                
                for name in names:
                    clean_name = clean_text(name)
                    if clean_name and clean_name not in existing_nacs:
                        nacs_to_create.append(Nacionalidad(nombre=clean_name))
                        existing_nacs.add(clean_name)
                        
                if nacs_to_create:
                    Nacionalidad.objects.bulk_create(nacs_to_create)
                return JsonResponse({"status": "success", "message": f"Se cargaron exitosamente {len(nacs_to_create)} nuevas nacionalidades desde el Excel en MAYÚSCULAS y SIN ACENTOS."})
            except Exception as e:
                return JsonResponse({"status": "error", "message": f"Error al procesar el catálogo de nacionalidades: {str(e)}"}, status=500)

        init_caches()
        
        if is_json:
            items_iterator = rows
        else:
            file_data = csv_file.read().decode("utf-8-sig")
            items_iterator = csv.DictReader(io.StringIO(file_data))
        
        chunk_size = 10000
        batch = []
        rows_processed = 0
        
        model_classes = {
            "canalizados_adultos": CanalizadoAdulto,
            "canalizados_nna": CanalizadoNNA,
            "condicion_estancia": CondicionEstancia,
            "motivo_estancia": MotivoEstancia,
            "encuentros": Encuentro,
            "extranjeros_recibidos": ExtranjeroRecibido,
            "inadmisiones": Inadmision,
            "internaciones": Internacion,
            "mexicanos_recibidos": MexicanoRecibido,
            "presentados": Presentado,
            "rescatados": Rescatado,
            "retornados": Retornado,
            "traslados": Traslado,
            "caravanas": Caravana,
            "actas_civil": ActasCivil,
            "tramites_migratorios": TramitesMigratorios,
            "inadmisiones2da": Inadmision2da,
            "internaciones_n": InternacionN,
            "mex_repatriados": MexRepatriados,
            "repatriados_comerciales": RepatriadosComerciales
        }
        
        model_class = model_classes.get(model_type)
        if not model_class:
            return JsonResponse({"status": "error", "message": "Tipo de modelo no reconocido."}, status=400)
            
        try:
            # If this is the first chunk of the upload session, clear existing data for this model
            is_first_chunk = False
            if is_json:
                chunk_index = data.get("chunk_index", 0)
                if chunk_index == 0:
                    is_first_chunk = True
            else:
                is_first_chunk = True

            if is_first_chunk:
                model_class.objects.all().delete()

            for idx, row in enumerate(items_iterator):
                # Clean headers and values by stripping whitespace, casting keys and values to strings
                row = {str(k).strip() if k is not None else "": str(v).strip() if v is not None else "" for k, v in row.items() if k is not None}
                
                if not any(row.values()):
                    continue
                
                try:
                    rows_added = process_row_to_batch(model_type, row, batch)
                    rows_processed += rows_added
                except Exception as row_error:
                    return JsonResponse({
                        "status": "error",
                        "message": f"Error en la fila {idx + 1} del lote: {str(row_error)}",
                        "row_index": idx
                    }, status=400)
                
                if len(batch) >= chunk_size:
                    try:
                        with transaction.atomic():
                            model_class.objects.bulk_create(batch, batch_size=2000)
                    except Exception as db_error:
                        return JsonResponse({
                            "status": "error",
                            "message": f"Error al guardar lote en la base de datos: {str(db_error)}"
                        }, status=400)
                    batch = []
            
            if batch:
                try:
                    with transaction.atomic():
                        model_class.objects.bulk_create(batch, batch_size=2000)
                except Exception as db_error:
                    return JsonResponse({
                        "status": "error",
                        "message": f"Error al guardar lote final en la base de datos: {str(db_error)}"
                    }, status=400)
                    
            return JsonResponse({"status": "success", "message": f"Se cargaron exitosamente {rows_processed} registros en MAYÚSCULAS y SIN ACENTOS."})
            
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error al procesar el archivo: {str(e)}"}, status=500)
            
    return render(request, "carga/upload.html")


@login_required
def carga_comparativo_view(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            return JsonResponse({"status": "error", "message": "No se seleccionó ningún archivo."}, status=400)
            
        try:
            # Open file with ZipFile to inspect cell fill styles (detect yellow headers FillId==2)
            import zipfile, xml.etree.ElementTree as ET
            
            yellow_rows = set()
            file.seek(0)
            try:
                with zipfile.ZipFile(file) as z:
                    shared_strings = []
                    if 'xl/sharedStrings.xml' in z.namelist():
                        ss_xml = z.read('xl/sharedStrings.xml')
                        ss_root = ET.fromstring(ss_xml)
                        for si in ss_root.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                            texts = [t.text for t in si.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') if t.text]
                            shared_strings.append(''.join(texts))

                    styles_xml = z.read('xl/styles.xml')
                    st_root = ET.fromstring(styles_xml)
                    cell_xfs = st_root.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}cellXfs')
                    
                    xf_fill_map = []
                    if cell_xfs is not None:
                        for xf in cell_xfs.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}xf'):
                            fill_id = int(xf.attrib.get('fillId', 0))
                            xf_fill_map.append(fill_id)

                    sheet1_xml = z.read('xl/worksheets/sheet1.xml')
                    s_root = ET.fromstring(sheet1_xml)
                    
                    for r in s_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
                        r_idx = int(r.attrib.get('r', 0))
                        cells = r.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
                        first_cell = next((c for c in cells if c.attrib.get('r', '').startswith('A')), None)
                        if first_cell is not None:
                            s_style = int(first_cell.attrib.get('s', 0))
                            fill_id = xf_fill_map[s_style] if s_style < len(xf_fill_map) else 0
                            # FillId 2 or FillId 3 correspond to category headers in yellow
                            if fill_id in [2, 3]:
                                yellow_rows.add(r_idx)
            except Exception as zip_err:
                print("Zip style parsing warning:", zip_err)

            file.seek(0)
            df_dict = pd.read_excel(file, sheet_name=None, header=None)
            sheet_name = list(df_dict.keys())[0]
            df = df_dict[sheet_name]
            
            # Map column indices to years (B=1 -> 2017, C=2 -> 2018, ... K=10 -> 2026)
            years_map = {}
            for col_idx in range(1, df.shape[1]):
                val = str(df.iloc[0, col_idx]).strip()
                if val.isdigit() and len(val) == 4:
                    years_map[col_idx] = int(val)
                elif not val or val == 'nan':
                    val2 = str(df.iloc[1, col_idx]).strip() if df.shape[0] > 1 else ''
                    if val2.isdigit() and len(val2) == 4:
                        years_map[col_idx] = int(val2)
                        
            if not years_map:
                for col_idx in range(1, min(11, df.shape[1])):
                    years_map[col_idx] = 2016 + col_idx

            metricas_batch = []
            
            def parse_num(val):
                if pd.isna(val) or str(val).strip() in ['', 'nan', 'None']:
                    return None
                try:
                    return int(float(str(val).replace(',', '').strip()))
                except ValueError:
                    return None

            current_category = "GENERAL"

            # Key category names list for fallback
            category_keywords = [
                'ACCIONES DE CONTROL', 'ACCIONES DE RESCATES', 'RESCATES', 'REINCIDENCIA',
                'EXTRANJEROS RECIBIDO', 'EXTRANJEROS RECIBIDOS', 'CARAVANAS', 'TRASLADOS DE NORTE A SUR',
                'TRASLADO DE NORTE A SUR', 'PRESUPUESTO', 'PLANTILLA', 'TRASLADOS A SU PAIS',
                'TRASLADOS A SU PAÍS', 'INGRESOS AL PAIS', 'INGRESOS AL PAÍS',
                'PERSONAS REGULARIZADAS', 'REPATRIADOS', 'SISTEMAS'
            ]

            for row_idx in range(df.shape[0]):
                excel_row_num = row_idx + 1
                first_cell = str(df.iloc[row_idx, 0]).strip() if pd.notna(df.iloc[row_idx, 0]) else ""
                clean_name = clean_text(first_cell)
                
                # Header row check (either in yellow_rows or in category_keywords)
                if excel_row_num in yellow_rows or any(kw in clean_name for kw in category_keywords):
                    if clean_name and clean_name not in ['INDICADOR', 'ANIO', 'AÑO']:
                        current_category = clean_name
                        continue
                
                if not clean_name or clean_name in ['ANIO', 'AÑO', 'INDICADOR']:
                    continue
                    
                # Process row values per year
                for col_idx, anio in years_map.items():
                    cell_val = df.iloc[row_idx, col_idx] if col_idx < df.shape[1] else None
                    
                    if current_category == 'SISTEMAS':
                        val_str = str(cell_val).strip() if pd.notna(cell_val) else ""
                        if val_str and val_str.lower() != 'nan':
                            metricas_batch.append(MetricaComparativa(
                                categoria='SISTEMAS',
                                subcategoria=clean_name,
                                anio=anio,
                                valor_texto=val_str
                            ))
                    else:
                        num_val = parse_num(cell_val)
                        if num_val is not None:
                            metricas_batch.append(MetricaComparativa(
                                categoria=current_category,
                                subcategoria=clean_name,
                                anio=anio,
                                valor_numero=num_val
                            ))

            with transaction.atomic():
                MetricaComparativa.objects.all().delete()
                MetricaComparativa.objects.bulk_create(metricas_batch, batch_size=2000)

            return JsonResponse({
                "status": "success", 
                "message": f"Se procesó e importó exitosamente la nueva estructura del Excel ({len(metricas_batch)} métricas registradas en PostgreSQL)."
            })

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error al procesar el archivo Excel: {str(e)}"}, status=500)

    return render(request, "carga/carga_comparativo.html")
