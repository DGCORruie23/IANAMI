import base64
from django.contrib.auth import logout, login, authenticate
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from .security import (
    generate_captcha_challenge,
    verify_captcha_solution,
    record_request_attempt,
    get_rate_limit_status,
    reset_user_rate_limit_on_success
)

def captcha_image_view(request):
    """
    Endpoint para refrescar o cargar la imagen del captcha vía GET.
    """
    token, img_bytes = generate_captcha_challenge()
    response = HttpResponse(img_bytes, content_type="image/png")
    response['X-Captcha-Token'] = token
    return response


def custom_login_view(request):
    """
    Vista de login personalizada que incluye:
      1. Rate limiting por usuario con bucket de 15 peticiones/min.
      2. Respuesta HTTP 429 con mensaje y tiempo de espera:
         - 1er fallo de límite: 1 minuto.
         - 2do fallo: 2 minutos.
         - 3er fallo: 4 minutos.
         - 4to fallo+: Bloqueado por todo el día.
      3. Desafío CAPTCHA 100% nativo y local (sin APIs de terceros).
    """
    # Si ya está autenticado, redirigir al inicio correspondiente
    if request.user.is_authenticated:
        redirect_to = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
        return redirect(redirect_to)

    rate_limit_error = None
    auth_error = None
    captcha_error = None
    is_blocked_429 = False

    username_input = request.POST.get('username', '').strip() if request.method == 'POST' else ''

    if request.method == 'POST':
        # 1. Verificar Rate Limit si se ingresó usuario
        if username_input:
            allowed, wait_seconds, is_day_blocked = record_request_attempt(username_input, max_requests_per_min=15)
            if not allowed:
                is_blocked_429 = True
                if is_day_blocked:
                    rate_limit_error = (
                        "Demasiados intentos fallidos. Su acceso para este usuario ha sido bloqueado por el resto del día."
                    )
                else:
                    mins = max(1, round(wait_seconds / 60))
                    rate_limit_error = (
                        f"Límite de intentos excedido (máximo 15 por minuto). "
                        f"Por favor espere {mins} minuto(s) ({wait_seconds} segundos) antes de intentar nuevamente."
                    )
        else:
            auth_error = "Por favor ingrese su usuario."

        # Si fue bloqueado por rate limit, respondemos con código 429
        if is_blocked_429:
            token, img_bytes = generate_captcha_challenge()
            captcha_base64 = base64.b64encode(img_bytes).decode('utf-8')
            context = {
                'captcha_token': token,
                'captcha_image_base64': captcha_base64,
                'rate_limit_error': rate_limit_error,
                'wait_seconds': wait_seconds,
                'is_day_blocked': is_day_blocked,
                'username_val': username_input,
                'status_code_429': True
            }
            return render(request, 'registration/login.html', context, status=429)

        # 2. Validar Captcha
        captcha_token = request.POST.get('captcha_token', '')
        captcha_response = request.POST.get('captcha_response', '').strip()

        if not verify_captcha_solution(captcha_token, captcha_response):
            captcha_error = "El código o resultado del Captcha es incorrecto o ha expirado. Intente nuevamente."

        # 3. Validar Autenticación si el Captcha es correcto
        password_input = request.POST.get('password', '')
        if not captcha_error:
            user = authenticate(request, username=username_input, password=password_input)
            if user is not None:
                login(request, user)
                reset_user_rate_limit_on_success(username_input)
                next_url = request.GET.get('next') or request.POST.get('next') or settings.LOGIN_REDIRECT_URL
                return redirect(next_url)
            else:
                auth_error = "Usuario o contraseña incorrectos. Por favor, inténtelo de nuevo."

    # Generar nuevo desafío Captcha
    token, img_bytes = generate_captcha_challenge()
    captcha_base64 = base64.b64encode(img_bytes).decode('utf-8')

    context = {
        'captcha_token': token,
        'captcha_image_base64': captcha_base64,
        'rate_limit_error': rate_limit_error,
        'auth_error': auth_error,
        'captcha_error': captcha_error,
        'username_val': username_input,
    }
    return render(request, 'registration/login.html', context)


def custom_logout_view(request):
    logout(request)
    return redirect('login')
