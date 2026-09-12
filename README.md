# VisionAI

VisionAI is a Django image-recognition application powered by MobileNetV2. Upload an image to receive a predicted class, confidence score, structured details, and related image suggestions. Authenticated users can keep recognition history and manage account preferences.

## Features

- MobileNetV2 image recognition for JPG, JPEG, PNG, and WEBP uploads
- Server-rendered Django dashboard with VisionAI navigation
- Sign up with full name, email, password confirmation, and validation
- Secure Django session authentication and password hashing
- Protected account page with the current user's name, email, and join date
- Per-user recognition history and saved preferences
- Wikipedia-backed descriptions with a local fallback when unavailable

## Requirements

- Python 3.11.11 (the Render deployment version)
- Django 6.1+
- Pillow
- NumPy
- TensorFlow
- A browser with JavaScript enabled

TensorFlow downloads the MobileNetV2 ImageNet weights the first time an image is analyzed. The initial prediction can therefore take longer than subsequent predictions.

The deployment uses Python 3.11.11 with `tensorflow-cpu==2.20.0`. Keep this pairing together: Render's Python 3.14 default is not supported by the pinned TensorFlow build. Render expects the bare version in `runtime.txt` (for example, `3.11.11`), not the `python-3.11.11` format used by some other hosting platforms.

## Setup

From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

Open the application at:

```text
http://127.0.0.1:8000/
```

Do not open `recognition/templates/recognition/index.html` directly and do not serve the templates with VS Code Live Server. Django must render the templates so `{% url %}` and authentication tags are processed correctly.

## Deploying on Render

The repository includes `render.yaml` with the complete web-service configuration. Create a new Render Blueprint from this repository. The blueprint provisions a PostgreSQL database, installs `requirements.txt`, collects static files, runs migrations, and starts Django with Gunicorn.

The equivalent Render commands are:

```text
Build: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
Start: gunicorn image_recognition.wsgi:application
```

The blueprint generates `DJANGO_SECRET_KEY`, sets production `DJANGO_DEBUG=False`, allows the Render hostname, and supplies `DATABASE_URL` from the provisioned database. For a manually created service, add those same environment variables in Render before the first deploy.

## Main Routes

| Route | Purpose |
| --- | --- |
| `/` | Image recognition dashboard |
| `/login/` | Sign in with email and password |
| `/register/` | Create an account |
| `/account/` | Protected current-user account page |
| `/logout/` | End the Django session |
| `/history/` | Recognition history view |
| `/explore/` | Supported recognition categories |
| `/modelinfo/` | Model information |
| `/settings/` | User preference settings |

## API Routes

- `POST /api/predict/` - Analyze an uploaded image
- `POST /api/signup/` - JSON registration endpoint
- `POST /api/login/` - JSON login endpoint
- `POST /api/logout/` - JSON logout endpoint
- `GET /api/me/` - Current authentication and profile status
- `GET` or `DELETE /api/history/` - Read or clear history for the current user
- `GET` or `POST /api/settings/` - Read or save authenticated preferences

## Testing

Run the Django checks and route/API smoke test:

```powershell
python manage.py check
python test_routes.py
```

The route smoke test includes password hashing, registration validation, login validation, session invalidation, settings persistence, prediction input validation, and per-user history isolation.

## Project Structure

```text
image_recognition/       Django project configuration
recognition/             Django application, views, models, URLs, and templates
recognition/templates/   Server-rendered VisionAI pages
static/                  Frontend assets
manage.py                Django command-line entry point
db.sqlite3               Local development database, ignored by Git
```

## Security Notes

This repository is configured for local development. Before deployment, move `SECRET_KEY` to an environment variable, set `DEBUG = False`, configure production `ALLOWED_HOSTS`, use a production database, and serve static/media files through a production-ready setup.
