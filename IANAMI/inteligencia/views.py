import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, F, Count, Q
from django.db.models.functions import TruncMonth
from datetime import date, timedelta
from carga.models import (
    Rescatado, Presentado, CanalizadoAdulto, CanalizadoNNA, Retornado,
    MexicanoRecibido, ExtranjeroRecibido, Inadmision, Internacion,
    Encuentro, CondicionEstancia, MotivoEstancia, Caravana, ActasCivil, TramitesMigratorios,
    InternacionN, MexRepatriados, RepatriadosComerciales
)
from usuario.permissions import get_user_role_info, admin_or_superuser_required

def format_month(dt):
    if not dt:
        return ""
    return dt.strftime("%Y-%m")

@login_required
@admin_or_superuser_required
def inteligencia_view(request):
    db_data = {}

    # 1. Rescatados
    res_m = {}
    for r in Rescatado.objects.annotate(month=TruncMonth('dia')).values('month').annotate(
        total=Sum('total'), pv=Sum('primera_vez'), rein=Sum('reincidencia'),
        em=Sum('presentados_em'), dif=Sum('canalizados_dif')
    ).order_by('month'):
        res_m[format_month(r['month'])] = {
            "total": r['total'] or 0, "pv": r['pv'] or 0, "rein": r['rein'] or 0,
            "em": r['em'] or 0, "dif": r['dif'] or 0
        }
    db_data["rescatados_monthly"] = res_m

    res_nac = {item['nacionalidad__nombre']: item['total'] or 0 for item in 
               Rescatado.objects.values('nacionalidad__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["rescatados_top_nac"] = res_nac

    res_or = {item['estado__estado__nombre']: item['total'] or 0 for item in 
              Rescatado.objects.values('estado__estado__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["rescatados_by_or"] = res_or

    # 2. Presentados
    pres_m = {format_month(item['month']): item['total'] or 0 for item in 
              Presentado.objects.annotate(month=TruncMonth('dia')).values('month').annotate(total=Sum('total')).order_by('month')}
    db_data["presentados_monthly"] = pres_m

    pres_nac = {item['nacionalidad__nombre']: item['total'] or 0 for item in 
                Presentado.objects.values('nacionalidad__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["presentados_top_nac"] = pres_nac

    pres_or = {item['estado__estado__nombre']: item['total'] or 0 for item in 
               Presentado.objects.values('estado__estado__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["presentados_by_or"] = pres_or

    # 3. Canalizados
    can_m = {}
    # Count adults
    adults_by_m = {format_month(item['month']): item['count'] for item in 
                   CanalizadoAdulto.objects.annotate(month=TruncMonth('dia')).values('month').annotate(count=Sum('id')).order_by('month')} # wait, just count occurrences
    # Let's count IDs
    from django.db.models import Count
    adults_by_m = {format_month(item['month']): item['count'] for item in 
                   CanalizadoAdulto.objects.annotate(month=TruncMonth('dia')).values('month').annotate(count=Count('id')).order_by('month')}
    nna_by_m = {format_month(item['month']): item['count'] for item in 
                CanalizadoNNA.objects.annotate(month=TruncMonth('dia')).values('month').annotate(count=Count('id')).order_by('month')}
    
    all_months = set(adults_by_m.keys()).union(nna_by_m.keys())
    for m in sorted(all_months):
        ad = adults_by_m.get(m, 0)
        nna = nna_by_m.get(m, 0)
        can_m[m] = {"total": ad + nna, "adultos": ad, "menores": nna}
    db_data["can_monthly"] = can_m

    # Top nationalities for NNA
    can_nac = {item['nacionalidad__nombre']: item['total'] or 0 for item in 
               CanalizadoNNA.objects.values('nacionalidad__nombre').annotate(total=Count('id')).order_by('-total')[:30]}
    db_data["can_top_nac"] = can_nac

    can_or = {item['estado__estado__nombre']: item['total'] or 0 for item in 
              CanalizadoNNA.objects.values('estado__estado__nombre').annotate(total=Count('id')).order_by('-total')[:30]}
    db_data["can_by_or"] = can_or

    # 4. Retornados
    ret_m = {}
    for r in Retornado.objects.annotate(month=TruncMonth('dia')).values('month').annotate(
        total=Sum('total'), dep=Sum('deportados'), asist=Sum('retornos_asistidos')
    ).order_by('month'):
        ret_m[format_month(r['month'])] = {
            "total": r['total'] or 0, "dep": r['dep'] or 0, "asist": r['asist'] or 0
        }
    db_data["retornados_monthly"] = ret_m

    ret_nac = {item['nacionalidad__nombre']: item['total'] or 0 for item in 
               Retornado.objects.values('nacionalidad__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["retornados_top_nac"] = ret_nac

    # 5. Mexicanos Recibidos (Repatriados)
    mx_m = {}
    for r in MexicanoRecibido.objects.annotate(month=TruncMonth('dia')).values('month').annotate(
        total=Sum('total'), adultos=Sum('adultos'), menores=Sum('menores'),
        nna_nc=Sum('nna_no_acompanados'), nna_ac=Sum('nna_acompanados'),
        terrestres=Sum('terrestres'), vuelos=Sum('vuelos')
    ).order_by('month'):
        mx_m[format_month(r['month'])] = {
            "total": r['total'] or 0, "adultos": r['adultos'] or 0, "menores": r['menores'] or 0,
            "nna_nc": r['nna_nc'] or 0, "nna_ac": r['nna_ac'] or 0,
            "terrestres": r['terrestres'] or 0, "vuelos": r['vuelos'] or 0
        }
    db_data["mx_monthly"] = mx_m

    mx_or = {item['estado__estado__nombre']: item['total'] or 0 for item in 
             MexicanoRecibido.objects.values('estado__estado__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["mx_by_or"] = mx_or

    # 6. Extranjeros Recibidos
    ext_m = {}
    for r in ExtranjeroRecibido.objects.annotate(month=TruncMonth('dia')).values('month').annotate(
        total=Sum('total'), adultos=Sum('adultos'), menores=Sum('menores')
    ).order_by('month'):
        ext_m[format_month(r['month'])] = {
            "total": r['total'] or 0, "adultos": r['adultos'] or 0, "menores": r['menores'] or 0
        }
    db_data["ext_monthly"] = ext_m

    ext_nac = {item['nacionalidad__nombre']: item['total'] or 0 for item in 
               ExtranjeroRecibido.objects.values('nacionalidad__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["ext_top_nac"] = ext_nac

    ext_or = {item['estado__estado__nombre']: item['total'] or 0 for item in 
              ExtranjeroRecibido.objects.values('estado__estado__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["ext_by_or"] = ext_or

    # 7. Inadmisiones
    inad_m = {format_month(item['month']): item['total'] or 0 for item in 
              Inadmision.objects.annotate(month=TruncMonth('dia')).values('month').annotate(total=Sum('total')).order_by('month')}
    db_data["inad_monthly"] = inad_m

    inad_nac = {item['nacionalidad__nombre']: item['total'] or 0 for item in 
                Inadmision.objects.values('nacionalidad__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["inad_top_nac"] = inad_nac

    # 8. Internaciones
    int_m = {}
    for r in Internacion.objects.annotate(month=TruncMonth('dia')).values('month').annotate(
        total=Sum('total'), aereo=Sum('aereo'), maritimo=Sum('maritimo'), terrestre=Sum('terrestre')
    ).order_by('month'):
        int_m[format_month(r['month'])] = {
            "total": r['total'] or 0, "aereo": r['aereo'] or 0, "maritimo": r['maritimo'] or 0,
            "terrestre": r['terrestre'] or 0
        }
    db_data["internaciones_monthly"] = int_m

    int_nac = {item['nacionalidad__nombre']: item['total'] or 0 for item in 
               Internacion.objects.values('nacionalidad__nombre').annotate(total=Sum('total')).order_by('-total')[:30]}
    db_data["internaciones_top_nac"] = int_nac

    # 9. Encuentros
    enc_m = {}
    for r in Encuentro.objects.annotate(month=TruncMonth('fecha')).values('month').annotate(
        total=Sum('total'), mexico=Sum('mexico'), extranjeros=Sum('extranjeros')
    ).order_by('month'):
        # Gather CBP / USBP counts if possible, otherwise generic estimates
        m_str = format_month(r['month'])
        enc_m[m_str] = {
            "total": r['total'] or 0, "mexico": r['mexico'] or 0, "extranjeros": r['extranjeros'] or 0,
            "usbp": Encuentro.objects.filter(fecha__year=r['month'].year, fecha__month=r['month'].month, encuentro='USBP').aggregate(s=Sum('total'))['s'] or 0,
            "ofo": Encuentro.objects.filter(fecha__year=r['month'].year, fecha__month=r['month'].month, encuentro='OFO').aggregate(s=Sum('total'))['s'] or 0,
            "cbpone": Encuentro.objects.filter(fecha__year=r['month'].year, fecha__month=r['month'].month, encuentro='CBP ONE').aggregate(s=Sum('total'))['s'] or 0
        }
    db_data["encuentros_monthly"] = enc_m

    # Top nationalities in Encuentros
    # Since it's stored in JSONField, we can aggregate via python memory for simplicity and accuracy
    enc_nac_totals = {}
    for enc in Encuentro.objects.all():
        for nac, val in enc.desglose_nacionalidades.items():
            enc_nac_totals[nac] = enc_nac_totals.get(nac, 0) + val
    db_data["encuentros_top_nac"] = dict(sorted(enc_nac_totals.items(), key=lambda x: x[1], reverse=True)[:30])

    enc_by_city = {}
    # Group by location (state/city)
    for item in Encuentro.objects.values('location', 'ciudad_mx').annotate(total=Sum('total')).order_by('-total')[:10]:
        enc_by_city[item['location'] or "Desconocido"] = {
            "total": item['total'] or 0,
            "estado": item['ciudad_mx'] or ""
        }
    db_data["encuentros_by_ciudad"] = enc_by_city

    # 10. Condicion de Estancia
    est_m = {}
    for r in CondicionEstancia.objects.annotate(month=TruncMonth('dia')).values('month').annotate(
        doc=Sum('documentos_migratorios'), res_perm=Sum('tarjeta_residente_permanente'),
        res_temp=Sum('tarjeta_residente_temporal'), res_est=Sum('tarjeta_residente_temporal_estudiante'),
        vis_hum=Sum('tarjeta_visitante_razones_humanitarias'), vis_adop=Sum('tarjeta_visitante_adopcion'),
        vis_reg=Sum('tarjeta_visitante_regional'), vis_front=Sum('tarjeta_visitante_trabajador_fronterizo')
    ).order_by('month'):
        est_m[format_month(r['month'])] = {
            "doc": r['doc'] or 0, "res_perm": r['res_perm'] or 0, "res_temp": r['res_temp'] or 0,
            "res_est": r['res_est'] or 0, "vis_hum": r['vis_hum'] or 0, "vis_adop": r['vis_adop'] or 0,
            "vis_reg": r['vis_reg'] or 0, "vis_front": r['vis_front'] or 0
        }
    db_data["estancia_monthly"] = est_m

    est_nac = {item['nacionalidad__nombre']: item['total'] or 0 for item in 
               CondicionEstancia.objects.values('nacionalidad__nombre').annotate(total=Sum('documentos_migratorios')).order_by('-total')[:30]}
    db_data["estancia_top_nac"] = est_nac

    est_or = {item['estado__estado__nombre']: item['total'] or 0 for item in 
              CondicionEstancia.objects.values('estado__estado__nombre').annotate(total=Sum('documentos_migratorios')).order_by('-total')[:30]}
    db_data["estancia_top_or"] = est_or

    # 11. Motivo Estancia
    mot_m = {format_month(item['month']): item['total'] or 0 for item in 
             MotivoEstancia.objects.annotate(month=TruncMonth('dia')).values('month').annotate(total=Sum('documentos_migratorios')).order_by('month')}
    db_data["motivo_monthly"] = mot_m

    mot_nac = {item['nacionalidad__nombre']: item['total'] or 0 for item in 
               MotivoEstancia.objects.values('nacionalidad__nombre').annotate(total=Sum('documentos_migratorios')).order_by('-total')[:30]}
    db_data["motivo_top_nac"] = mot_nac

    mot_or = {item['estado__estado__nombre']: item['total'] or 0 for item in 
              MotivoEstancia.objects.values('estado__estado__nombre').annotate(total=Sum('documentos_migratorios')).order_by('-total')[:30]}
    db_data["motivo_top_or"] = mot_or

    mot_by_m = {item['motivo_estancia']: item['total'] or 0 for item in 
                MotivoEstancia.objects.values('motivo_estancia').annotate(total=Sum('documentos_migratorios')).order_by('-total')[:30]}
    db_data["motivo_by_motivo"] = mot_by_m

    # 12. Caravanas
    caravanas_list = []
    for c in Caravana.objects.all().order_by('-dia'):
        caravanas_list.append({
            "dia": c.dia.strftime("%Y-%m-%d"),
            "año": str(c.anio),
            "estado_partida": c.estado_partida.estado.nombre if c.estado_partida else "",
            "lugar_partida": c.lugar_partida or "",
            "nombre": c.nombre or "",
            "estado_disolucion": c.estado_disolucion.estado.nombre if c.estado_disolucion else "",
            "lugar_disolucion": c.lugar_disolucion or "",
            "personas_inicio": c.personas_inicio,
            "personas_rescatadas": c.personas_rescatadas,
            "personas_documentadas": c.personas_documentadas,
            "tipo_doc": c.tipo_documento or "",
            "tvrh": c.tvrh, "pam": c.pam, "fmm": c.fmm, "cita_comar": c.cita_comar,
            "docs_provisionales": c.docs_provisionales,
            "nacionalidades": c.desglose_nacionalidades
        })
    db_data["caravanas"] = caravanas_list
    db_data["caravanas_all"] = caravanas_list  # Use same data or subset

    # Inyectar JSON seguro en el contexto del template
    db_json = json.dumps(db_data)
    
    return render(request, 'inteligencia/ianami.html', {'db_json': db_json})

@login_required
def indicadores_view(request):
    role_info = get_user_role_info(request.user)
    return render(request, 'inteligencia/indicadores.html', {
        'user_role': role_info,
    })

from carga.models import (
    Rescatado, Presentado, CanalizadoAdulto, CanalizadoNNA, Retornado,
    MexicanoRecibido, ExtranjeroRecibido, Inadmision, Internacion,
    Encuentro, CondicionEstancia, MotivoEstancia, Caravana, ActasCivil, TramitesMigratorios,
    InternacionN, MetricaComparativa
)

@login_required
@admin_or_superuser_required
def comparativo_view(request):
    return render(request, 'inteligencia/comparativo.html')

@login_required
def comparativo_data_view(request):
    # Fetch all metrics stored in BD
    metrics_qs = MetricaComparativa.objects.all().values('categoria', 'subcategoria', 'anio', 'valor_numero', 'valor_texto')
    
    # Structure data by Category -> Subcategory -> Year
    data_by_category = {}
    for item in metrics_qs:
        cat = item['categoria']
        sub = item['subcategoria']
        anio = item['anio']
        val_num = item['valor_numero']
        val_txt = item['valor_texto']
        
        if cat not in data_by_category:
            data_by_category[cat] = {}
        if sub not in data_by_category[cat]:
            data_by_category[cat][sub] = {}
            
        data_by_category[cat][sub][anio] = val_num if val_num is not None else val_txt

    return JsonResponse({"status": "success", "data": data_by_category})

@login_required
def indicadores_data_view(request):
    # Get latest date in DB or default to today
    latest_record = ActasCivil.objects.order_by('-fecha_solicitud').first()
    ref_date = latest_record.fecha_solicitud if latest_record else date.today()

    weeks = []
    # Dynamic weeks - 8 weeks (about 2 months back)
    for i in range(12): # Let's support up to 12 weeks to matches the image which has 12 columns
        end_date = ref_date - timedelta(days=i * 7)
        start_date = end_date - timedelta(days=6)
        weeks.append((start_date, end_date))
    
    # Reverse so they are chronological (from oldest to newest)
    weeks.reverse()
    
    labels = []
    matrimonios = []
    nacimientos = []
    totales = []
    
    top_state_mat_volumes = []
    top_state_mat_names = []
    top_state_nac_volumes = []
    top_state_nac_names = []
    
    # Map months in Spanish
    months_es = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    for start_date, end_date in weeks:
        # Label: e.g., "17 Jul - 23 Jul"
        label = f"{start_date.day} {months_es[start_date.month]} - {end_date.day} {months_es[end_date.month]}"
        labels.append(label)
        
        # Query ActasCivil in this week range
        qs = ActasCivil.objects.filter(fecha_solicitud__range=(start_date, end_date))
        
        # Total
        total_count = qs.count()
        totales.append(total_count)
        
        # Matrimonios (clean_text saves as UPPERCASE, so it matches MATRIMONIO)
        mat_count = qs.filter(tipo_acto='MATRIMONIO').count()
        matrimonios.append(mat_count)
        
        # Nacimientos
        nac_count = qs.filter(tipo_acto='NACIMIENTO').count()
        nacimientos.append(nac_count)
        
        # Top Entidad for all validation registrations
        entidad_counts = qs.values('entidad').annotate(count=Count('id')).order_by('-count')
        if entidad_counts.exists() and total_count > 0:
            top_state_mat = entidad_counts[0]
            top_state_mat_names.append(top_state_mat['entidad'])
            top_state_mat_volumes.append(top_state_mat['count'])
        else:
            top_state_mat_names.append("S/D")
            top_state_mat_volumes.append(0)

        # Top Estado (OR) for all validation registrations
        estado_counts = qs.values('estado__nombre').annotate(count=Count('id')).order_by('-count')
        if estado_counts.exists() and total_count > 0:
            top_state_nac = estado_counts[0]
            top_state_nac_names.append(top_state_nac['estado__nombre'])
            top_state_nac_volumes.append(top_state_nac['count'])
        else:
            top_state_nac_names.append("S/D")
            top_state_nac_volumes.append(0)
            
    # Calculate percentage change for chart 1 (total)
    pct_change_total = 0.0
    if len(totales) >= 2:
        prev = totales[-2]
        curr = totales[-1]
        if prev > 0:
            pct_change_total = ((curr - prev) / prev) * 100.0
            
    # Calculate percentage change for Matrimonios top state volume
    pct_change_mat_state = 0.0
    if len(top_state_mat_volumes) >= 2:
        prev = top_state_mat_volumes[-2]
        curr = top_state_mat_volumes[-1]
        if prev > 0:
            pct_change_mat_state = ((curr - prev) / prev) * 100.0

    # Calculate percentage change for Nacimientos top state volume
    pct_change_nac_state = 0.0
    if len(top_state_nac_volumes) >= 2:
        prev = top_state_nac_volumes[-2]
        curr = top_state_nac_volumes[-1]
        if prev > 0:
            pct_change_nac_state = ((curr - prev) / prev) * 100.0

    # Summary data for bullet points
    last_total = totales[-1] if totales else 0
    last_mat = matrimonios[-1] if matrimonios else 0
    last_nac = nacimientos[-1] if nacimientos else 0
    prev_total = totales[-2] if len(totales) >= 2 else 0
    
    last_mat_pct = round((last_mat / last_total * 100), 1) if last_total > 0 else 0
    last_nac_pct = round((last_nac / last_total * 100), 1) if last_total > 0 else 0
    
    last_top_state_mat = top_state_mat_names[-1] if top_state_mat_names else "S/D"
    prev_top_state_mat = top_state_mat_names[-2] if len(top_state_mat_names) >= 2 else "S/D"

    last_top_state_nac = top_state_nac_names[-1] if top_state_nac_names else "S/D"
    prev_top_state_nac = top_state_nac_names[-2] if len(top_state_nac_names) >= 2 else "S/D"

    # Nationality breakdown helper for the last two weeks
    def get_nationality_breakdown(start_date, end_date):
        qs = ActasCivil.objects.filter(fecha_solicitud__range=(start_date, end_date))
        total = qs.count()
        if total == 0:
            return {"total": 0, "breakdown": [], "concentration_pct": 0, "others": {"count": 0, "pct": 0}}
            
        nac_counts = qs.values('nacionalidad__nombre').annotate(count=Count('id')).order_by('-count')
        
        breakdown = []
        top_sum = 0
        
        top_5 = list(nac_counts[:5])
        for item in top_5:
            count = item['count']
            pct = round((count / total) * 100)
            # Make nationality name capital case or title case (e.g. CUBANA)
            raw_name = item['nacionalidad__nombre'] or "DESCONOCIDA"
            # Format nicely, e.g. "Cubana"
            formatted_name = raw_name.title() + "a" if not raw_name.endswith("a") and not raw_name.endswith("o") else raw_name.title()
            # If name is "Colombia" -> "Colombiana", "Cuba" -> "Cubana", "Honduras" -> "Hondureña", "Guatemala" -> "Guatemalteca", "Estados Unidos" -> "Estadounidense"
            # Let's map them explicitly or keep title case
            name_map = {
                "CUBA": "Cubana",
                "COLOMBIA": "Colombiana",
                "ESTADOS UNIDOS": "Estadounidense",
                "HONDURAS": "Hondureña",
                "GUATEMALA": "Guatemalteca",
                "VENEZUELA": "Venezolana",
                "EL SALVADOR": "Salvadoreña",
                "NICARAGUA": "Nicaragüense",
                "HAITI": "Haitiana",
                "MEXICO": "Mexicana"
            }
            clean_raw = raw_name.upper().strip()
            name_label = name_map.get(clean_raw, raw_name.title())
            
            breakdown.append({
                "name": name_label,
                "count": count,
                "pct": pct
            })
            top_sum += count
            
        others_count = total - top_sum
        others_pct = round((others_count / total) * 100)
        concentration_pct = round((top_sum / total) * 100)
        
        # Format week header label, e.g. "del 13 al 17 de julio"
        week_label = f"del {start_date.day} {months_es[start_date.month].lower()} al {end_date.day} {months_es[end_date.month].lower()}"
        
        return {
            "total": total,
            "breakdown": breakdown,
            "others": {"count": others_count, "pct": others_pct},
            "concentration_pct": concentration_pct,
            "week_label": week_label
        }

    last_week_breakdown = {}
    prev_week_breakdown = {}
    if len(weeks) >= 2:
        last_week_breakdown = get_nationality_breakdown(weeks[-1][0], weeks[-1][1])
        prev_week_breakdown = get_nationality_breakdown(weeks[-2][0], weeks[-2][1])

    data = {
        "labels": labels,
        "matrimonios": matrimonios,
        "nacimientos": nacimientos,
        "totales": totales,
        "top_state_mat_volumes": top_state_mat_volumes,
        "top_state_mat_names": top_state_mat_names,
        "top_state_nac_volumes": top_state_nac_volumes,
        "top_state_nac_names": top_state_nac_names,
        "pct_change_total": round(pct_change_total, 2),
        "pct_change_mat_state": round(pct_change_mat_state, 2),
        "pct_change_nac_state": round(pct_change_nac_state, 2),
        "summary": {
            "last_total": last_total,
            "prev_total": prev_total,
            "last_mat": last_mat,
            "last_nac": last_nac,
            "last_mat_pct": last_mat_pct,
            "last_nac_pct": last_nac_pct,
            "last_top_state_mat": last_top_state_mat,
            "prev_top_state_mat": prev_top_state_mat,
            "last_top_state_nac": last_top_state_nac,
            "prev_top_state_nac": prev_top_state_nac,
        },
        "last_week_breakdown": last_week_breakdown,
        "prev_week_breakdown": prev_week_breakdown
    }
    return JsonResponse(data)


@login_required
def tramites_data_view(request):
    tramite_param = request.GET.get('tramite')
    
    # If no tramite parameter is passed, return the list of unique procedures
    if not tramite_param:
        tramites_list = list(
            TramitesMigratorios.objects
            .values_list('tramite', flat=True)
            .distinct()
            .order_by('tramite')
        )
        # Clean empty/None values and title-case them for the frontend dropdown list if desired,
        # but keep them exactly as they are in the database.
        tramites_list = [t for t in tramites_list if t]
        return JsonResponse({
            "status": "success",
            "tramites": tramites_list
        })
        
    # Standardize search term to match uppercase clean format in DB
    selected_tramite = str(tramite_param).strip().upper()
    
    # Identify chronological 12 week periods going back from the latest record
    latest_record = TramitesMigratorios.objects.filter(tramite=selected_tramite).order_by('-fecha').first()
    ref_date = latest_record.fecha if latest_record else date.today()
    
    # Align ref_date to nearest Sunday
    while ref_date.weekday() != 6:
        ref_date += timedelta(days=1)
        
    weeks = []
    for i in range(12):
        end_date = ref_date - timedelta(days=i * 7)
        start_date = end_date - timedelta(days=6)
        weeks.append((start_date, end_date))
    weeks.reverse()
    
    overall_start = weeks[0][0]
    overall_end = weeks[-1][1]
    
    # Identify top 2 states for this procedure based on overall received volumes
    top_states_qs = (
        TramitesMigratorios.objects
        .filter(tramite=selected_tramite, fecha__range=(overall_start, overall_end))
        .values('estado__nombre')
        .annotate(total=Sum('recibidos'))
        .order_by('-total')[:2]
    )
    
    default_state1 = top_states_qs[0]['estado__nombre'] if len(top_states_qs) >= 1 else "S/D"
    default_state2 = top_states_qs[1]['estado__nombre'] if len(top_states_qs) >= 2 else "S/D"

    req_state1 = request.GET.get('estado1')
    req_state2 = request.GET.get('estado2')

    if req_state1 == "NONE":
        state1 = None
    elif req_state1 and req_state1.strip():
        state1 = req_state1.strip().upper()
    else:
        state1 = default_state1

    if req_state2 == "NONE":
        state2 = None
    elif req_state2 and req_state2.strip():
        state2 = req_state2.strip().upper()
    else:
        state2 = default_state2

    # Get list of all distinct states for dropdowns
    all_states_qs = (
        TramitesMigratorios.objects
        .filter(tramite=selected_tramite)
        .values_list('estado__nombre', flat=True)
        .distinct()
        .order_by('estado__nombre')
    )
    estados_list = [e.title() for e in all_states_qs if e]
    
    def get_metric_data(metric_field):
        labels = []
        nac_values = []
        state1_values = [] if state1 else None
        state2_values = [] if state2 else None
        
        for start_date, end_date in weeks:
            label = f"{start_date.day}/{start_date.month}/{start_date.year}"
            labels.append(label)
            
            qs_week = TramitesMigratorios.objects.filter(tramite=selected_tramite, fecha__range=(start_date, end_date))
            
            total_nac = qs_week.aggregate(total=Sum(metric_field))['total'] or 0
            nac_values.append(total_nac)
            
            if state1:
                total_s1 = qs_week.filter(estado__nombre=state1).aggregate(total=Sum(metric_field))['total'] or 0
                state1_values.append(total_s1)
            
            if state2:
                total_s2 = qs_week.filter(estado__nombre=state2).aggregate(total=Sum(metric_field))['total'] or 0
                state2_values.append(total_s2)
            
        # Calculate percentage change for the last week vs previous week
        pct_change_nac = 0.0
        if len(nac_values) >= 2 and nac_values[-2] > 0:
            pct_change_nac = ((nac_values[-1] - nac_values[-2]) / nac_values[-2]) * 100.0
            
        pct_change_s1 = 0.0
        if state1 and len(state1_values) >= 2 and state1_values[-2] > 0:
            pct_change_s1 = ((state1_values[-1] - state1_values[-2]) / state1_values[-2]) * 100.0
            
        pct_change_s2 = 0.0
        if state2 and len(state2_values) >= 2 and state2_values[-2] > 0:
            pct_change_s2 = ((state2_values[-1] - state2_values[-2]) / state2_values[-2]) * 100.0
            
        # Top nationality analysis in the last week
        last_week_start, last_week_end = weeks[-1]
        qs_last = TramitesMigratorios.objects.filter(tramite=selected_tramite, fecha__range=(last_week_start, last_week_end))
        
        def get_top_nac_info(qs_filter, total_val):
            if total_val <= 0:
                return {"name": "S/D", "count": 0, "pct": 0}
            nac_counts = (
                qs_filter
                .values('nacionalidad__nombre')
                .annotate(total_sum=Sum(metric_field))
                .order_by('-total_sum')
            )
            if nac_counts.exists() and nac_counts[0]['total_sum'] > 0:
                top_item = nac_counts[0]
                pct = round((top_item['total_sum'] / total_val) * 100)
                
                raw_name = top_item['nacionalidad__nombre'] or "DESCONOCIDA"
                # Nicer title case formats
                name_map = {
                    "ESTADOS UNIDOS": "EEUU",
                    "ESTADOUNIDENSE": "EEUU",
                    "CHINA": "China",
                    "COLOMBIA": "Colombia",
                    "VENEZUELA": "Venezuela"
                }
                clean_name = name_map.get(raw_name.upper().strip(), raw_name.title())
                return {
                    "name": clean_name,
                    "count": top_item['total_sum'],
                    "pct": pct
                }
            return {"name": "S/D", "count": 0, "pct": 0}
            
        top_nac_national = get_top_nac_info(qs_last, nac_values[-1])
        
        res = {
            "labels": labels,
            "nacional": {
                "values": nac_values,
                "pct_change": round(pct_change_nac, 1),
                "top_nationality": top_nac_national
            }
        }

        if state1:
            top_nac_s1 = get_top_nac_info(qs_last.filter(estado__nombre=state1), state1_values[-1])
            import statistics
            s1_mean = round(statistics.mean(state1_values), 1) if state1_values else 0
            try:
                s1_mode = round(statistics.mode(state1_values), 1) if state1_values else 0
            except statistics.StatisticsError:
                s1_mode = None
            s1_std = round(statistics.stdev(state1_values), 1) if len(state1_values) > 1 else 0

            res["state1"] = {
                "name": state1.title(),
                "values": state1_values,
                "pct_change": round(pct_change_s1, 1),
                "top_nationality": top_nac_s1,
                "stats": {
                    "mean": s1_mean,
                    "mode": s1_mode,
                    "std_dev": s1_std
                }
            }

        if state2:
            top_nac_s2 = get_top_nac_info(qs_last.filter(estado__nombre=state2), state2_values[-1])
            import statistics
            s2_mean = round(statistics.mean(state2_values), 1) if state2_values else 0
            try:
                s2_mode = round(statistics.mode(state2_values), 1) if state2_values else 0
            except statistics.StatisticsError:
                s2_mode = None
            s2_std = round(statistics.stdev(state2_values), 1) if len(state2_values) > 1 else 0

            res["state2"] = {
                "name": state2.title(),
                "values": state2_values,
                "pct_change": round(pct_change_s2, 1),
                "top_nationality": top_nac_s2,
                "stats": {
                    "mean": s2_mean,
                    "mode": s2_mode,
                    "std_dev": s2_std
                }
            }

        return res
        
    data = {
        "status": "success",
        "tramite": tramite_param,
        "selected_state1": state1.title() if state1 else "NONE",
        "selected_state2": state2.title() if state2 else "NONE",
        "estados": estados_list,
        "recibidos": get_metric_data("recibidos"),
        "concluidos": get_metric_data("concluidos"),
        "resueltos": get_metric_data("resueltos"),
        "proceso": get_metric_data("proceso")
    }
    return JsonResponse(data)


@login_required
def control_data_view(request):
    from django.db.models import Q
    from datetime import date

    # Filter from Jan 1 2025 onwards
    start_filter_date = date(2025, 1, 1)
    qs_2025 = InternacionN.objects.filter(dia__gte=start_filter_date)

    months_es = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    # Group by month
    months_qs = (
        qs_2025
        .annotate(m=TruncMonth('dia'))
        .values('m')
        .annotate(
            tot_sum=Sum('total'),
            aereo_sum=Sum('total', filter=Q(tipoIngreso__tipo__icontains='AEREO')),
            terr_sum=Sum('total', filter=Q(tipoIngreso__tipo__icontains='TERRESTRE')),
            mar_sum=Sum('total', filter=Q(tipoIngreso__tipo__icontains='MARITIMO'))
        )
        .order_by('m')
    )

    labels = []
    totales = []
    aereos = []
    terrestres = []
    maritimos = []

    for item in months_qs:
        dt = item['m']
        if dt:
            lbl = f"{months_es[dt.month]} {dt.year}"
            labels.append(lbl)
            totales.append(item['tot_sum'] or 0)
            aereos.append(item['aereo_sum'] or 0)
            terrestres.append(item['terr_sum'] or 0)
            maritimos.append(item['mar_sum'] or 0)

    # Calculate percentage change for chart 1 total (last vs prev month)
    pct_change_total = 0.0
    if len(totales) >= 2 and totales[-2] > 0:
        pct_change_total = ((totales[-1] - totales[-2]) / totales[-2]) * 100.0

    # Top 5 Aéreo airports (puntos de internación aéreos)
    aereo_qs = qs_2025.filter(tipoIngreso__tipo__icontains='AEREO')
    tot_aereo = aereo_qs.aggregate(s=Sum('total'))['s'] or 1

    map_ap = {}
    for r in aereo_qs.values('puntoInternacion').annotate(t=Sum('total')):
        name = r['puntoInternacion'] or 'DESCONOCIDO'
        clean = name.upper()
        if 'CANCUN' in clean:
            key = 'AI Cancún'
        elif 'CIUDAD DE MEXICO' in clean or 'MEXICO' in clean:
            key = 'AICM'
        elif 'GUADALAJARA' in clean:
            key = 'AI Guadalajara'
        elif 'LOS CABOS' in clean or 'CABOS' in clean:
            key = 'AI Los Cabos'
        elif 'PUERTO VALLARTA' in clean or 'VALLARTA' in clean:
            key = 'AI Puerto Vallarta'
        elif 'MONTERREY' in clean:
            key = 'AI Monterrey'
        else:
            key = name.title()
        map_ap[key] = map_ap.get(key, 0) + (r['t'] or 0)

    sorted_ap = sorted(map_ap.items(), key=lambda x: x[1], reverse=True)[:5]
    top5_sum = sum(x[1] for x in sorted_ap)
    concentration_pct = round((top5_sum / tot_aereo) * 100, 2)

    top5_formatted = []
    for name, val in sorted_ap:
        pct = round((val / tot_aereo) * 100, 2)
        top5_formatted.append({
            "name": name,
            "count": val,
            "pct": pct
        })

    last_total = totales[-1] if totales else 0
    prev_total = totales[-2] if len(totales) >= 2 else 0

    # Inadmision2da data (Jan 2025 onwards)
    from carga.models import Inadmision2da
    qs_inad2 = Inadmision2da.objects.filter(dia__gte=start_filter_date)

    months_inad_qs = (
        qs_inad2
        .annotate(m=TruncMonth('dia'))
        .values('m')
        .annotate(
            tot_sum=Sum('total'),
            rechazo_sum=Sum('total', filter=Q(determinacion__icontains='RECHAZO')),
            internacion_sum=Sum('total', filter=Q(determinacion__icontains='INTERNACION'))
        )
        .order_by('m')
    )

    inad_labels = []
    inad_totales = []
    inad_rechazos = []
    inad_internaciones = []

    for item in months_inad_qs:
        dt = item['m']
        if dt:
            lbl = f"{months_es[dt.month]} {dt.year}"
            inad_labels.append(lbl)
            inad_totales.append(item['tot_sum'] or 0)
            inad_rechazos.append(item['rechazo_sum'] or 0)
            inad_internaciones.append(item['internacion_sum'] or 0)

    pct_change_inad = 0.0
    if len(inad_totales) >= 2 and inad_totales[-2] > 0:
        pct_change_inad = ((inad_totales[-1] - inad_totales[-2]) / inad_totales[-2]) * 100.0

    tot_g_inad = qs_inad2.aggregate(s=Sum('total'))['s'] or 1

    map_ap_inad = {}
    for r in qs_inad2.values('puntoInternacion').annotate(t=Sum('total')):
        name = r['puntoInternacion'] or 'DESCONOCIDO'
        clean = name.upper()
        if 'CANCUN' in clean:
            key = 'AI Cancún'
        elif 'CIUDAD DE MEXICO' in clean or 'MEXICO' in clean:
            key = 'AICM'
        elif 'GUADALAJARA' in clean:
            key = 'AI Guadalajara'
        elif 'LOS CABOS' in clean or 'CABOS' in clean:
            key = 'AI Los Cabos'
        elif 'TIJUANA' in clean:
            key = 'Tijuana (Puerta México)'
        elif 'PUERTO VALLARTA' in clean or 'VALLARTA' in clean:
            key = 'AI Puerto Vallarta'
        else:
            key = name.title()
        map_ap_inad[key] = map_ap_inad.get(key, 0) + (r['t'] or 0)

    sorted_ap_inad = sorted(map_ap_inad.items(), key=lambda x: x[1], reverse=True)[:5]
    top5_sum_inad = sum(x[1] for x in sorted_ap_inad)
    concentration_pct_inad = round((top5_sum_inad / tot_g_inad) * 100, 2)

    top5_inad_formatted = []
    for name, val in sorted_ap_inad:
        pct = round((val / tot_g_inad) * 100, 2)
        top5_inad_formatted.append({
            "name": name,
            "count": val,
            "pct": pct
        })

    data = {
        "status": "success",
        "labels": labels,
        "totales": totales,
        "aereos": aereos,
        "terrestres": terrestres,
        "maritimos": maritimos,
        "pct_change_total": round(pct_change_total, 2),
        "top5_airports": top5_formatted,
        "concentration_pct": concentration_pct,
        "summary": {
            "last_total": last_total,
            "prev_total": prev_total
        },
        "inadmision2da": {
            "labels": inad_labels,
            "totales": inad_totales,
            "rechazos": inad_rechazos,
            "internaciones": inad_internaciones,
            "pct_change_total": round(pct_change_inad, 2),
            "top5_points": top5_inad_formatted,
            "concentration_pct": concentration_pct_inad,
            "summary": {
                "last_total": inad_totales[-1] if inad_totales else 0,
                "prev_total": inad_totales[-2] if len(inad_totales) >= 2 else 0,
                "last_rechazo": inad_rechazos[-1] if inad_rechazos else 0,
                "last_internacion": inad_internaciones[-1] if inad_internaciones else 0
            }
        }
    }
    return JsonResponse(data)


@login_required
def proteccion_data_view(request):
    months_es = {
        1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
        5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
        9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE"
    }

    latest_record = MexRepatriados.objects.order_by('-fecha').first()
    if not latest_record:
        return JsonResponse({
            "status": "success",
            "has_data": False,
            "weeks_bar": [],
            "table_data": [],
            "table_total": {},
            "two_weeks_headers": {"prev": "SEM PREVIA", "last": "SEM ACTUAL"},
            "current_year": date.today().year
        })

    ref_date = latest_record.fecha
    current_year = ref_date.year

    # Construir las 6 semanas consecutivas hacia atrás de 7 días cada una
    # semana 0 (más reciente): [ref_date - 6 días, ref_date]
    # semana 1: [ref_date - 13 días, ref_date - 7 días], etc.
    weeks = []
    for i in range(6):
        end_d = ref_date - timedelta(days=i * 7)
        start_d = end_d - timedelta(days=6)
        weeks.append((start_d, end_d))
    weeks.reverse() # Orden cronológico: [Sem 1 (más antigua), ..., Sem 6 (más reciente)]

    # Filtro base para considerar únicamente aeropuertos (AEROPUERTO, A.I, A. I)
    airport_filter = (
        Q(puntoInternación__icontains='AEROPUERTO') |
        Q(puntoInternación__icontains='A.I') |
        Q(puntoInternación__icontains='A. I')
    )

    qs_airports_base = MexRepatriados.objects.filter(airport_filter)

    weeks_bar = []
    for start_d, end_d in weeks:
        qs_w = qs_airports_base.filter(fecha__range=(start_d, end_d))
        tot_repatriados = qs_w.aggregate(s=Sum('total'))['s'] or 0
        vuelos_count = qs_w.count()

        if start_d.month == end_d.month:
            label = f"{start_d.day:02d} AL {end_d.day:02d} DE {months_es[start_d.month]}"
        else:
            label = f"{start_d.day:02d} DE {months_es[start_d.month]} AL {end_d.day:02d} DE {months_es[end_d.month]}"

        weeks_bar.append({
            "label": label,
            "start_date": start_d.strftime("%Y-%m-%d"),
            "end_date": end_d.strftime("%Y-%m-%d"),
            "total_repatriados": tot_repatriados,
            "vuelos": vuelos_count
        })

    # Últimas dos semanas para contrastar en la tabla
    prev_w_start, prev_w_end = weeks[-2]
    last_w_start, last_w_end = weeks[-1]

    def fmt_week_header(s_d, e_d):
        if s_d.month == e_d.month:
            return f"DEL {s_d.day:02d} AL {e_d.day:02d} DE {months_es[s_d.month]}"
        return f"DEL {s_d.day:02d} DE {months_es[s_d.month]} AL {e_d.day:02d} DE {months_es[e_d.month]}"

    two_weeks_headers = {
        "prev": fmt_week_header(prev_w_start, prev_w_end),
        "last": fmt_week_header(last_w_start, last_w_end)
    }

    # Obtener puntos de aeropuertos únicos
    raw_points = list(qs_airports_base.values_list('puntoInternación', flat=True).distinct())
    raw_points = [p for p in raw_points if p]

    def clean_airport_display_name(pt):
        p = pt.upper().strip()
        if 'TAPACHULA' in p:
            return 'TAPACHULA'
        if 'VILLAHERMOSA' in p:
            return 'VILLAHERMOSA'
        if 'FELIPE ANGELES' in p or 'AIFA' in p:
            return 'AIFA'
        if 'TULUM' in p:
            return 'TULUM'
        if 'MORELIA' in p:
            return 'MORELIA'
        if 'HUATULCO' in p:
            return 'HUATULCO'
        if 'MERIDA' in p or 'MÉRIDA' in p:
            return 'MÉRIDA'
        if 'CAMPECHE' in p:
            return 'CAMPECHE'
        if 'SAN LUIS POTOSI' in p or 'SAN LUIS POTOSÍ' in p:
            return 'SAN LUIS POTOSÍ'
        if 'GUADALAJARA' in p:
            return 'GUADALAJARA'
        if 'MONTERREY' in p:
            return 'MONTERREY'
        if 'CIUDAD DE MEXICO' in p or 'AICM' in p or 'CDMX' in p:
            return 'CIUDAD DE MÉXICO'
        
        # Fallback genérico
        p = p.replace('AEROPUERTO INTERNACIONAL DE', '').replace('AEROPUERTO INTERNACIONAL', '')
        p = p.replace('A. I.', '').replace('A.I.', '').replace('A.I', '').replace('OR. CHIAPAS /', '')
        p = p.replace('"', '').strip()
        return p or pt.upper().strip()

    # Mapear cada nombre normalizado con su lista de strings en BD (para evitar duplicados como Monterrey)
    airport_groups = {}
    for raw_pt in raw_points:
        norm_name = clean_airport_display_name(raw_pt)
        if norm_name not in airport_groups:
            airport_groups[norm_name] = []
        airport_groups[norm_name].append(raw_pt)

    table_data = []
    
    tot_prev_vuelos = 0
    tot_last_vuelos = 0
    tot_prev_rep = 0
    tot_last_rep = 0
    tot_year_vuelos = 0
    tot_year_rep = 0

    # Consultar por cada grupo de aeropuertos normalizado
    for display_name, pts_list in airport_groups.items():
        qs_pt_all = qs_airports_base.filter(puntoInternación__in=pts_list)
        qs_pt_year = qs_pt_all.filter(fecha__year=current_year)
        
        y_vuelos = qs_pt_year.count()
        y_rep = qs_pt_year.aggregate(s=Sum('total'))['s'] or 0

        qs_prev = qs_pt_all.filter(fecha__range=(prev_w_start, prev_w_end))
        v_prev = qs_prev.count()
        r_prev = qs_prev.aggregate(s=Sum('total'))['s'] or 0

        qs_last = qs_pt_all.filter(fecha__range=(last_w_start, last_w_end))
        v_last = qs_last.count()
        r_last = qs_last.aggregate(s=Sum('total'))['s'] or 0

        # Si no tiene actividad en las últimas semanas ni en el año en curso
        if v_prev == 0 and v_last == 0 and y_vuelos == 0 and y_rep == 0:
            continue

        dif_vuelos = v_last - v_prev
        dif_rep = r_last - r_prev

        table_data.append({
            "punto": display_name,
            "vuelos_prev": v_prev,
            "vuelos_last": v_last,
            "vuelos_dif": dif_vuelos,
            "rep_prev": r_prev,
            "rep_last": r_last,
            "rep_dif": dif_rep,
            "year_vuelos": y_vuelos,
            "year_rep": y_rep
        })

        tot_prev_vuelos += v_prev
        tot_last_vuelos += v_last
        tot_prev_rep += r_prev
        tot_last_rep += r_last
        tot_year_vuelos += y_vuelos
        tot_year_rep += y_rep

    # Ordenar por repatriados de la última semana descendente, luego acumulado anual
    table_data.sort(key=lambda x: (x['rep_last'], x['year_rep']), reverse=True)

    table_total = {
        "vuelos_prev": tot_prev_vuelos,
        "vuelos_last": tot_last_vuelos,
        "vuelos_dif": tot_last_vuelos - tot_prev_vuelos,
        "rep_prev": tot_prev_rep,
        "rep_last": tot_last_rep,
        "rep_dif": tot_last_rep - tot_prev_rep,
        "year_vuelos": tot_year_vuelos,
        "year_rep": tot_year_rep
    }

    # =========================================================================
    # SECCIÓN COMERCIALES (RepatriadosComerciales)
    # =========================================================================
    latest_com = RepatriadosComerciales.objects.order_by('-fecha').first()
    com_has_data = False
    com_weeks_bar = []
    com_table_data = []
    com_table_total = {}
    com_two_weeks_headers = {"prev": "SEM PREVIA", "last": "SEM ACTUAL"}
    com_current_year = date.today().year

    if latest_com:
        com_has_data = True
        com_ref_date = latest_com.fecha
        com_current_year = com_ref_date.year

        com_weeks = []
        for i in range(6):
            end_d = com_ref_date - timedelta(days=i * 7)
            start_d = end_d - timedelta(days=6)
            com_weeks.append((start_d, end_d))
        com_weeks.reverse()

        for start_d, end_d in com_weeks:
            qs_w = RepatriadosComerciales.objects.filter(fecha__range=(start_d, end_d))
            tot_rep = qs_w.aggregate(s=Sum('total'))['s'] or 0
            vuelos_cnt = qs_w.count()

            if start_d.month == end_d.month:
                lbl = f"{start_d.day:02d} AL {end_d.day:02d} DE {months_es[start_d.month]}"
            else:
                lbl = f"{start_d.day:02d} DE {months_es[start_d.month]} AL {end_d.day:02d} DE {months_es[end_d.month]}"

            com_weeks_bar.append({
                "label": lbl,
                "start_date": start_d.strftime("%Y-%m-%d"),
                "end_date": end_d.strftime("%Y-%m-%d"),
                "total_repatriados": tot_rep,
                "vuelos": vuelos_cnt
            })

        c_prev_w_start, c_prev_w_end = com_weeks[-2]
        c_last_w_start, c_last_w_end = com_weeks[-1]

        com_two_weeks_headers = {
            "prev": fmt_week_header(c_prev_w_start, c_prev_w_end),
            "last": fmt_week_header(c_last_w_start, c_last_w_end)
        }

        com_raw_points = list(RepatriadosComerciales.objects.values_list('puntoInternación', flat=True).distinct())
        com_raw_points = [p for p in com_raw_points if p]

        def clean_com_airport_name(pt):
            p = pt.upper().strip()
            if 'CANCUN' in p or 'CANCÚN' in p:
                return 'A.I. DE CANCÚN'
            if 'GUADALAJARA' in p:
                return 'A.I. DE GUADALAJARA'
            if 'MONTERREY' in p:
                return 'A.I. DE MONTERREY'
            if 'PUERTO VALLARTA' in p or 'VALLARTA' in p:
                return 'A.I. DE PUERTO VALLARTA'
            if 'CIUDAD DE MEXICO' in p or 'CIUDAD MEXICO' in p or 'CDMX' in p or 'AICM' in p:
                return 'A.I. DE LA CIUDAD DE MÉXICO'
            if 'CABOS' in p:
                return 'A.I. DE LOS CABOS'
            if 'HERMOSILLO' in p:
                return 'A.I. DE HERMOSILLO'
            if 'QUERETARO' in p or 'QUERETAEO' in p or 'QUERÉTARO' in p:
                return 'A.I. DE QUERÉTARO'
            if 'ZIHUATANEJO' in p or 'IXTAPA' in p:
                return 'A.I. DE IXTAPA ZIHUATANEJO'
            if 'MORELIA' in p:
                return 'A.I. DE MORELIA'
            if 'MERIDA' in p or 'MÉRIDA' in p:
                return 'A.I. DE MÉRIDA'
            if 'SAN LUIS POTOSI' in p or 'SAN LUIS POTOSÍ' in p:
                return 'A.I. DE SAN LUIS POTOSÍ'
            if 'CAMPECHE' in p:
                return 'A.I. DE CAMPECHE'
            if 'HUATULCO' in p:
                return 'A.I. DE HUATULCO'
            if 'TAPACHULA' in p:
                return 'A.I. DE TAPACHULA'
            if 'VILLAHERMOSA' in p:
                return 'A.I. DE VILLAHERMOSA'
            return f"A.I. DE {p.replace('AEROPUERTO INTERNACIONAL DE', '').replace('AEROPUERTO INTERNACIONAL', '').replace('A.I.', '').strip()}"

        com_groups = {}
        for raw_pt in com_raw_points:
            norm_name = clean_com_airport_name(raw_pt)
            if norm_name not in com_groups:
                com_groups[norm_name] = []
            com_groups[norm_name].append(raw_pt)

        c_tot_prev_rep = 0
        c_tot_last_rep = 0
        c_tot_year_rep = 0

        for display_name, pts_list in com_groups.items():
            qs_pt_all = RepatriadosComerciales.objects.filter(puntoInternación__in=pts_list)
            qs_pt_year = qs_pt_all.filter(fecha__year=com_current_year)
            y_rep = qs_pt_year.aggregate(s=Sum('total'))['s'] or 0

            qs_prev = qs_pt_all.filter(fecha__range=(c_prev_w_start, c_prev_w_end))
            r_prev = qs_prev.aggregate(s=Sum('total'))['s'] or 0

            qs_last = qs_pt_all.filter(fecha__range=(c_last_w_start, c_last_w_end))
            r_last = qs_last.aggregate(s=Sum('total'))['s'] or 0

            if r_prev == 0 and r_last == 0 and y_rep == 0:
                continue

            dif_rep = r_last - r_prev

            com_table_data.append({
                "punto": display_name,
                "rep_prev": r_prev,
                "rep_last": r_last,
                "rep_dif": dif_rep,
                "year_rep": y_rep
            })

            c_tot_prev_rep += r_prev
            c_tot_last_rep += r_last
            c_tot_year_rep += y_rep

        com_table_data.sort(key=lambda x: (x['rep_last'], x['year_rep']), reverse=True)

        com_table_total = {
            "rep_prev": c_tot_prev_rep,
            "rep_last": c_tot_last_rep,
            "rep_dif": c_tot_last_rep - c_tot_prev_rep,
            "year_rep": c_tot_year_rep
        }

    # =========================================================================
    # SECCIÓN NNA'S POR CONDICIÓN DE ACOMPAÑAMIENTO (MexRepatriados)
    # =========================================================================
    nna_months_qs = (
        MexRepatriados.objects
        .filter(fecha__year=current_year)
        .annotate(m=TruncMonth('fecha'))
        .values('m')
        .annotate(
            tot_acomp=Sum('acompañados'),
            tot_solos=Sum('solos')
        )
        .order_by('m')
    )

    nna_chart_labels = []
    nna_chart_acomp = []
    nna_chart_solos = []
    nna_table_data = []

    tot_nna_acomp_year = 0
    tot_nna_solos_year = 0
    tot_nna_total_year = 0

    prev_month_total = None

    for item in nna_months_qs:
        dt = item['m']
        if not dt:
            continue
        m_name = months_es[dt.month]
        ac = item['tot_acomp'] or 0
        so = item['tot_solos'] or 0
        tot = ac + so

        nna_chart_labels.append(m_name)
        nna_chart_acomp.append(ac)
        nna_chart_solos.append(so)

        dif_str = ""
        dif_val = None
        if prev_month_total is not None and prev_month_total > 0:
            dif_pct = round(((tot - prev_month_total) / prev_month_total) * 100)
            dif_val = dif_pct
            dif_str = f"+{dif_pct}%" if dif_pct > 0 else f"{dif_pct}%"
        elif prev_month_total is not None and prev_month_total == 0 and tot > 0:
            dif_str = "+100%"

        nna_table_data.append({
            "mes": m_name,
            "acompanados": ac,
            "solos": so,
            "total": tot,
            "diferencia": dif_str,
            "dif_val": dif_val
        })

        tot_nna_acomp_year += ac
        tot_nna_solos_year += so
        tot_nna_total_year += tot

        prev_month_total = tot

    pct_acomp_year = round((tot_nna_acomp_year / tot_nna_total_year) * 100) if tot_nna_total_year > 0 else 0
    pct_solos_year = round((tot_nna_solos_year / tot_nna_total_year) * 100) if tot_nna_total_year > 0 else 0

    nna_summary = {
        "tot_acomp": tot_nna_acomp_year,
        "tot_solos": tot_nna_solos_year,
        "tot_total": tot_nna_total_year,
        "pct_acomp": pct_acomp_year,
        "pct_solos": pct_solos_year
    }

    return JsonResponse({
        "status": "success",
        "has_data": True,
        "weeks_bar": weeks_bar,
        "table_data": table_data,
        "table_total": table_total,
        "two_weeks_headers": two_weeks_headers,
        "current_year": current_year,
        "comerciales": {
            "has_data": com_has_data,
            "weeks_bar": com_weeks_bar,
            "table_data": com_table_data,
            "table_total": com_table_total,
            "two_weeks_headers": com_two_weeks_headers,
            "current_year": com_current_year
        },
        "nna": {
            "has_data": len(nna_table_data) > 0,
            "chart_labels": nna_chart_labels,
            "chart_acomp": nna_chart_acomp,
            "chart_solos": nna_chart_solos,
            "table_data": nna_table_data,
            "summary": nna_summary,
            "current_year": current_year
        }
    })


