# ProstoPetition

ProstoPetition — клієнт-серверний вебзастосунок для створення, перегляду, модерації та підтримки електронних петицій.

Backend реалізовано на Django REST Framework. Frontend реалізовано на Vue.js. Обмін даними між клієнтом і сервером виконується через REST API у форматі JSON. Основна СУБД — MySQL.

## Структура проєкту

accounts/ — реєстрація, вхід, вихід, CSRF і профіль користувача.
petitions/ — категорії, петиції, модерація, статуси та офіційні відповіді.
voting/ — логіка голосування.
frontend/ — Vue.js клієнтська частина.
ProstoPetition/ — конфігурація Django-проєкту.
requirements.txt — Python-залежності.
frontend/package.json — Node.js-залежності.
Dockerfile, docker-compose.yml — конфігурація контейнерного середовища.

## Ролі команди

Backend Developer — Django, REST API, моделі, бізнес-логіка та MySQL.
Frontend Developer — Vue.js, компоненти, сторінки, маршрутизація та робота з API.
Full-stack / QА — інтеграція frontend і backend, конфігурація середовища та перевірка сумісності компонентів.

## Основні API

GET /api/auth/csrf/
GET /api/auth/profile/
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/logout/

GET, POST /api/categories/
GET, PATCH, DELETE /api/categories/{id}/

GET, POST /api/petitions/
GET, DELETE /api/petitions/{id}/
POST /api/petitions/{id}/vote/
PATCH /api/petitions/{id}/status/
POST /api/petitions/{id}/response/

GET /api/admin/petitions/
GET /api/admin/statistics/

## Backend

Python 3.13+ та MySQL.

Створити і активувати віртуальне середовище:

python -m venv .venv

Windows PowerShell:
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

Задати змінні середовища:

export DJANGO_DEBUG=1
export MYSQL_DATABASE=prostopetition
export MYSQL_USER=prostopetition
export MYSQL_PASSWORD='password'
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3306

Виконати міграції:

python manage.py migrate

За потреби створити адміністратора:

python manage.py createsuperuser

Запустити Django:

python manage.py runserver

Backend буде доступний за адресою http://127.0.0.1:8000.

## Frontend

cd frontend

Встановити залежності:

npm install

npm ci
Запустити Vite:

npm run dev

Frontend використовує шлях /api. Під час локальної розробки Vite проксіює API-запити на Django за адресою http://127.0.0.1:8000.
