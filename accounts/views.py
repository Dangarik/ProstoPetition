import json
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from petitions.models import Petition

def error(message, status=400):
    return JsonResponse({"detail": message}, status=status)

def payload(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None

def user_json(user):
    return {"id": user.id, "username": user.username, "email": user.email, "is_staff": user.is_staff}

@require_GET
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})

@csrf_protect
@require_POST
def register(request):
    data = payload(request)
    if data is None:
        return error("Очікується JSON-об’єкт.")
    username, email, password = (data.get(k) for k in ("username", "email", "password"))
    if not all(isinstance(x, str) and x.strip() for x in (username, email, password)):
        return error("Потрібні username, email і password.")
    username, email = username.strip(), email.strip().lower()
    User = get_user_model()
    if User.objects.filter(email__iexact=email).exists():
        return error("Цю електронну адресу вже зареєстровано.")
    user = User(username=username, email=email)
    try:
        user.full_clean(exclude=["password"])
        validate_password(password, user)
        with transaction.atomic():
            user.set_password(password)
            user.save()
    except ValidationError as exc:
        return JsonResponse({"errors": exc.message_dict if hasattr(exc, "message_dict") else {"password": exc.messages}}, status=400)
    except IntegrityError:
        return error("Ім’я або електронна адреса вже зайняті.")
    login(request, user)
    return JsonResponse({"user": user_json(user)}, status=201)

@csrf_protect
@require_POST
def login_view(request):
    data = payload(request)
    if data is None:
        return error("Очікується JSON-об’єкт.")
    user = authenticate(request, username=data.get("username"), password=data.get("password"))
    if user is None:
        return error("Неправильне ім’я користувача або пароль.", 400)
    login(request, user)
    return JsonResponse({"user": user_json(user)})

@csrf_protect
@require_POST
def logout_view(request):
    if not request.user.is_authenticated:
        return error("Потрібна авторизація.", 403)
    logout(request)
    return JsonResponse({"detail": "Сеанс завершено."})

@require_GET
def profile(request):
    if not request.user.is_authenticated:
        return error("Потрібна авторизація.", 403)
    petitions = Petition.objects.filter(author=request.user).order_by("-created_at").values("id", "title", "status", "created_at")
    return JsonResponse({"user": user_json(request.user), "petitions": list(petitions)})

def csrf_failure(request, reason=""):
    return error("CSRF-токен відсутній або недійсний.", 403)

