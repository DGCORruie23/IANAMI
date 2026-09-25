from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden, JsonResponse

# Mapping from area abbreviation to section ID in indicadores.html
AREA_SECTIONS = {
    'DGRAM': 'regulacion',
    'DGCVM': 'control',
    'DGPMV': 'proteccion',
}

# Mapping from area abbreviation to allowed model_types in upload_csv
AREA_MODELS = {
    'DGRAM': [
        'actas_civil',
        'tramites_migratorios',
        # 'condicion_estancia',
        # 'motivo_estancia',
    ],
    'DGCVM': [
        # 'rescatados',
        # 'presentados',
        # 'canalizados_adultos',
        # 'canalizados_nna',
        # 'internaciones',
        # 'inadmisiones',
        'inadmisiones2da',
        'internaciones_n',
        # 'encuentros',
        # 'extranjeros_recibidos',
        # 'retornados',
        # 'traslados',
        # 'caravanas',
    ],
    'DGPMV': [
        # 'mexicanos_recibidos',
        'mex_repatriados',
        'repatriados_comerciales',
    ],
}


def get_user_role_info(user):
    """
    Returns permission details for the given user.
    Types:
      1: Administrador -> Acceso a todas las URLs, ve todas las secciones, sube todos los tipos de excel.
      2: Editor        -> Acceso a 'indicadores' y 'upload_csv'.
                          En 'indicadores' solo ve la sección de su área (DGRAM -> Regulación, DGCVM -> Control, DGPMV -> Protección).
                          En 'upload_csv' solo sube modelos de su área.
      3: Visualizador  -> Solo acceso a 'indicadores', ve todo el template.
    """
    if not user or not user.is_authenticated:
        return {
            'is_admin': False,
            'is_editor': False,
            'is_viewer': False,
            'tipo': None,
            'tipo_nombre': 'Anónimo',
            'area_abrev': '',
            'area_nombre': '',
            'allowed_sections': [],
            'can_view_all_sections': False,
            'can_upload': False,
            'can_access_dashboard': False,
        }

    # Superuser has total admin access
    if user.is_superuser:
        return {
            'is_admin': True,
            'is_editor': False,
            'is_viewer': False,
            'tipo': '1',
            'tipo_nombre': 'Administrador (Superusuario)',
            'area_abrev': '',
            'area_nombre': 'Acceso Total',
            'allowed_sections': ['regulacion', 'control', 'proteccion'],
            'can_view_all_sections': True,
            'can_upload': True,
            'can_access_dashboard': True,
        }

    perfil = getattr(user, 'perfil', None)
    if not perfil:
        if user.is_staff:
            return {
                'is_admin': True,
                'is_editor': False,
                'is_viewer': False,
                'tipo': '1',
                'tipo_nombre': 'Administrador',
                'area_abrev': '',
                'area_nombre': 'Administración',
                'allowed_sections': ['regulacion', 'control', 'proteccion'],
                'can_view_all_sections': True,
                'can_upload': True,
                'can_access_dashboard': True,
            }
        # Default fallback for users without profile: Visualizador
        return {
            'is_admin': False,
            'is_editor': False,
            'is_viewer': True,
            'tipo': '3',
            'tipo_nombre': 'Visualizador',
            'area_abrev': '',
            'area_nombre': 'Sin Área Asignada',
            'allowed_sections': ['regulacion', 'control', 'proteccion'],
            'can_view_all_sections': True,
            'can_upload': False,
            'can_access_dashboard': False,
        }

    tipo = str(perfil.tipo).strip()
    area = perfil.area
    area_abrev = area.abreviatura_dg.strip().upper() if (area and area.abreviatura_dg) else ''
    area_nombre = area.nombre_dg if area else ''

    if tipo == '1':  # Administrador
        return {
            'is_admin': True,
            'is_editor': False,
            'is_viewer': False,
            'tipo': '1',
            'tipo_nombre': 'Administrador',
            'area_abrev': area_abrev,
            'area_nombre': area_nombre,
            'allowed_sections': ['regulacion', 'control', 'proteccion'],
            'can_view_all_sections': True,
            'can_upload': True,
            'can_access_dashboard': True,
        }
    elif tipo == '2':  # Editor
        section = AREA_SECTIONS.get(area_abrev)
        allowed_sections = [section] if section else ['regulacion', 'control', 'proteccion']
        return {
            'is_admin': False,
            'is_editor': True,
            'is_viewer': False,
            'tipo': '2',
            'tipo_nombre': 'Editor',
            'area_abrev': area_abrev,
            'area_nombre': area_nombre,
            'allowed_sections': allowed_sections,
            'can_view_all_sections': False,
            'can_upload': True,
            'can_access_dashboard': False,
        }
    else:  # Visualizador (tipo == '3' o cualquier otro)
        return {
            'is_admin': False,
            'is_editor': False,
            'is_viewer': True,
            'tipo': '3',
            'tipo_nombre': 'Visualizador',
            'area_abrev': area_abrev,
            'area_nombre': area_nombre,
            'allowed_sections': ['regulacion', 'control', 'proteccion'],
            'can_view_all_sections': True,
            'can_upload': False,
            'can_access_dashboard': False,
        }


def admin_or_superuser_required(view_func):
    """
    Decorator for views that can only be accessed by Admin or Superuser.
    Non-admin users are redirected to 'indicadores'.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        role = get_user_role_info(request.user)
        if not role['is_admin']:
            return redirect('indicadores')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def upload_permission_required(view_func):
    """
    Decorator for upload view: allows Admin, Superuser, and Editor.
    Visualizers and unauthenticated users are redirected to 'indicadores'.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        role = get_user_role_info(request.user)
        if not role['can_upload']:
            return redirect('indicadores')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
