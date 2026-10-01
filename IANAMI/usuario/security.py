import io
import time
import random
import math
from PIL import Image, ImageDraw, ImageFont
from django.core.signing import Signer, BadSignature
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache

signer = Signer(salt='ianami.captcha')

def generate_captcha_challenge():
    """
    Genera un desafío CAPTCHA puramente local sin APIs externas.
    Soporta operaciones matemáticas simples (ej: 8 + 5 = ?) y cadenas alfanuméricas legibles.
    Retorna: (token_firmado, image_bytes_png)
    """
    mode = random.choice(['math', 'text'])
    if mode == 'math':
        a = random.randint(3, 15)
        b = random.randint(2, 12)
        op = random.choice(['+', '-'])
        if op == '+':
            solution = str(a + b)
            display_text = f"{a} + {b} = ?"
        else:
            if a < b:
                a, b = b, a
            solution = str(a - b)
            display_text = f"{a} - {b} = ?"
    else:
        # Caracteres no ambiguos (evitamos 0/O, 1/I/l)
        chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        solution = ''.join(random.choices(chars, k=5))
        display_text = solution

    width, height = 200, 56
    # Fondo con textura suave acorde a la paleta del proyecto (#FAFAF8 / #F2F0E8)
    img = Image.new('RGB', (width, height), color=(247, 246, 240))
    draw = ImageDraw.Draw(img)

    # Ruido de fondo: puntos y líneas aleatorias
    for _ in range(120):
        xy = (random.randint(0, width), random.randint(0, height))
        draw.point(xy, fill=(random.randint(180, 220), random.randint(180, 210), random.randint(160, 200)))

    for _ in range(4):
        x1, y1 = random.randint(0, width // 3), random.randint(0, height)
        x2, y2 = random.randint(width // 2, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(160, 200), random.randint(160, 190), random.randint(140, 180)), width=1)

    # Dibujar caracteres con ligera rotación y espaciado (tamaño aumentado +4 puntos)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        except IOError:
            font = ImageFont.load_default()

    start_x = 16
    # Colores oscuros de la paleta IA-NAMI: #2C2C2A, #B66666, #778E88, #4A4A48
    dark_colors = [(44, 44, 42), (182, 102, 102), (119, 142, 136), (74, 74, 72)]
    for ch in display_text:
        char_color = random.choice(dark_colors)
        draw.text((start_x, random.randint(8, 14)), ch, font=font, fill=char_color)
        start_x += random.randint(19, 24)

    # Ondulación sinusoidal suave
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_bytes = buf.getvalue()

    # Payload firmado: solución + timestamp de creación (válido 5 minutos)
    payload = f"{solution.upper()}:{int(time.time())}"
    token = signer.sign(payload)
    return token, img_bytes


def verify_captcha_solution(token, user_input, max_age_seconds=300):
    """
    Valida el token firmado y la respuesta del usuario.
    Retorna True si es válido y no ha expirado.
    """
    if not token or not user_input:
        return False
    try:
        unsigned = signer.unsign(token)
        solution, created_at = unsigned.split(':', 1)
        created_at = int(created_at)
        if time.time() - created_at > max_age_seconds:
            return False  # Expiró
        return str(user_input).strip().upper() == solution.upper()
    except (BadSignature, ValueError):
        return False


# ==========================================
# LÓGICA DE TOKEN BUCKET & EXPONENTIAL BACKOFF
# ==========================================
def get_rate_limit_status(username):
    """
    Verifica el estado de rate limit y bloqueos para un nombre de usuario.
    Retorna (is_blocked: bool, wait_seconds: int, is_day_blocked: bool, attempts: int)
    """
    user_key = f"rl:user:{username.strip().lower()}"
    state = cache.get(user_key)
    now = time.time()

    if not state:
        return False, 0, False, 0

    blocked_until = state.get('blocked_until', 0)
    day_blocked = state.get('day_blocked', False)

    if day_blocked:
        # Bloqueado hasta el fin del día (o 24 horas)
        remaining = int(blocked_until - now)
        if remaining > 0:
            return True, remaining, True, state.get('strikes', 0)
        else:
            # Ya pasó el periodo de 24h
            cache.delete(user_key)
            return False, 0, False, 0

    if blocked_until > now:
        remaining = int(blocked_until - now)
        return True, remaining, False, state.get('strikes', 0)

    # Limpiar timestamps de la ventana de 1 minuto (Token bucket / Sliding window)
    timestamps = [t for t in state.get('timestamps', []) if now - t <= 60]
    return False, 0, False, state.get('strikes', 0)


def record_request_attempt(username, max_requests_per_min=15):
    """
    Registra una petición de login para el usuario.
    Si excede 15 peticiones en 1 minuto:
      - Strike 1: Bloqueo de 1 minuto (60s)
      - Strike 2: Bloqueo de 2 minutos (120s)
      - Strike 3: Bloqueo de 4 minutos (240s)
      - Strike 4+: Bloqueo por todo el día (86400s)
    Retorna: (allowed: bool, wait_seconds: int, is_day_blocked: bool)
    """
    user_key = f"rl:user:{username.strip().lower()}"
    now = time.time()
    state = cache.get(user_key) or {
        'timestamps': [],
        'strikes': 0,
        'blocked_until': 0,
        'day_blocked': False
    }

    # Si ya estaba bloqueado
    if state['day_blocked']:
        remaining = int(state['blocked_until'] - now)
        if remaining > 0:
            return False, remaining, True
        else:
            # Reseteo al pasar el día
            state = {'timestamps': [], 'strikes': 0, 'blocked_until': 0, 'day_blocked': False}

    if state['blocked_until'] > now:
        return False, int(state['blocked_until'] - now), False

    # Filtrar ventana de 60 segundos
    timestamps = [t for t in state.get('timestamps', []) if now - t <= 60]
    timestamps.append(now)
    state['timestamps'] = timestamps

    # Verificar si excede las 15 peticiones por minuto
    if len(timestamps) > max_requests_per_min:
        strikes = state.get('strikes', 0) + 1
        state['strikes'] = strikes
        state['timestamps'] = []  # Vaciar bucket para el siguiente ciclo

        if strikes == 1:
            wait_time = 60      # 1 minuto
            state['day_blocked'] = False
        elif strikes == 2:
            wait_time = 120     # 2 minutos
            state['day_blocked'] = False
        elif strikes == 3:
            wait_time = 240     # 4 minutos
            state['day_blocked'] = False
        else:
            wait_time = 86400   # Todo el día (24 horas)
            state['day_blocked'] = True

        state['blocked_until'] = now + wait_time
        # Guardar en cache por al menos 24 horas + 1 hora
        cache.set(user_key, state, timeout=90000)
        return False, wait_time, state['day_blocked']

    cache.set(user_key, state, timeout=90000)
    return True, 0, False


def reset_user_rate_limit_on_success(username):
    """
    Opcional: Si el login es exitoso, reseteamos timestamps (o eliminamos cache)
    para que el usuario legítimo pueda operar con normalidad.
    """
    user_key = f"rl:user:{username.strip().lower()}"
    cache.delete(user_key)
