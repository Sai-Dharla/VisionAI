import json
from pathlib import Path
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .utils import predict_image
from .models import PredictionHistory, UserPreference

ALLOWED_EXT = {'.jpg', '.jpeg', '.png', '.webp'}

def index(request):
    """Recognize page (dashboard default tab)."""
    return render(request, 'recognition/index.html', {'active_tab': 'Recognize'})

@csrf_exempt
def predict(request):
    """Process image upload, run MobileNetV2 prediction, and save to history."""
    if request.method != 'POST' or 'image' not in request.FILES:
        return JsonResponse({'error': 'POST request with an "image" file required.'}, status=400)

    uploaded = request.FILES['image']
    ext = Path(uploaded.name).suffix.lower()
    if ext not in ALLOWED_EXT:
        return JsonResponse({'error': f'Unsupported file type "{ext}". Allowed: {", ".join(ALLOWED_EXT)}.'}, status=400)

    try:
        result = predict_image(uploaded)
        
        # Save to database history (respect the user's auto-save preference)
        user = request.user if request.user.is_authenticated else None
        if user is None or getattr(getattr(user, 'preference', None), 'auto_save_history', True):
            PredictionHistory.objects.create(
                user=user,
                image_name=uploaded.name,
                class_name=result.get('class_name', 'Unknown'),
                subtitle=result.get('subtitle', ''),
                confidence=result.get('confidence', '0%'),
                tag=result.get('tag', 'Object'),
                description=result.get('description', '')
            )
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({'error': f"An error occurred during recognition: {str(exc)}"}, status=500)

    return JsonResponse(result)

@csrf_exempt
def api_signup(request):
    """User Registration API."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)
    
    try:
        data = json.loads(request.body.decode('utf-8'))
        username = data.get('username', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', password)

        if not username or not email or not password:
            return JsonResponse({'error': 'Username, email and password are required.'}, status=400)

        # Email format validation
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'error': 'Please enter a valid email address.'}, status=400)

        # Password strength validation
        if len(password) < 8:
            return JsonResponse({'error': 'Password must be at least 8 characters long.'}, status=400)

        # Password confirmation check
        if password != confirm_password:
            return JsonResponse({'error': 'Passwords do not match.'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username is already taken.'}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'An account with this email already exists.'}, status=400)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        UserPreference.objects.create(user=user)
        login(request, user)

        return JsonResponse({
            'success': True,
            'user': {
                'username': user.username,
                'email': user.email,
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_login(request):
    """User Login API."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)
    
    try:
        data = json.loads(request.body.decode('utf-8'))
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if email and not username:
            username = User.objects.filter(email__iexact=email).values_list('username', flat=True).first() or ''

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Ensure UserPreference exists
            UserPreference.objects.get_or_create(user=user)
            return JsonResponse({
                'success': True,
                'user': {
                    'username': user.username,
                    'email': user.email,
                }
            })
        else:
            return JsonResponse({'error': 'Invalid username or password.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_logout(request):
    """User Logout API."""
    logout(request)
    return JsonResponse({'success': True})

def api_me(request):
    """Get current logged-in user profile & authentication status."""
    if request.user.is_authenticated:
        pref, _ = UserPreference.objects.get_or_create(user=request.user)
        return JsonResponse({
            'authenticated': True,
            'user': {
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'date_joined': request.user.date_joined.strftime('%B %d, %Y'),
                'images_analyzed': request.user.predictions.count(),
            },
            'preferences': {
                'theme': pref.theme,
                'auto_save_history': pref.auto_save_history,
                'show_wikipedia_summary': pref.show_wikipedia_summary,
            }
        })
    else:
        return JsonResponse({'authenticated': False})

@csrf_exempt
def api_history(request):
    """GET user scan history or DELETE entries."""
    if request.method == 'GET':
        if request.user.is_authenticated:
            qs = PredictionHistory.objects.filter(user=request.user)
        else:
            qs = PredictionHistory.objects.filter(user=None)[:25]
        
        history_list = [
            {
                'id': h.id,
                'image_name': h.image_name,
                'class_name': h.class_name,
                'subtitle': h.subtitle,
                'confidence': h.confidence,
                'tag': h.tag,
                'description': h.description,
                'created_at': h.created_at.strftime('%b %d, %Y %I:%M %p')
            }
            for h in qs
        ]
        return JsonResponse({'history': history_list})

    elif request.method == 'DELETE':
        if request.user.is_authenticated:
            PredictionHistory.objects.filter(user=request.user).delete()
        else:
            PredictionHistory.objects.filter(user=None).delete()
        return JsonResponse({'success': True})

@csrf_exempt
def api_settings(request):
    """GET or POST user settings."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)
    
    pref, _ = UserPreference.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            pref.theme = data.get('theme', pref.theme)
            pref.auto_save_history = data.get('auto_save_history', pref.auto_save_history)
            pref.show_wikipedia_summary = data.get('show_wikipedia_summary', pref.show_wikipedia_summary)
            pref.save()

            if 'email' in data:
                request.user.email = data['email']
                request.user.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({
        'theme': pref.theme,
        'auto_save_history': pref.auto_save_history,
        'show_wikipedia_summary': pref.show_wikipedia_summary,
        'email': request.user.email
    })


def history(request):
    """History page (same dashboard, History tab active)."""
    return render(request, 'recognition/index.html', {'active_tab': 'History'})

def explore(request):
    """Explore page (same dashboard, Explore tab active)."""
    return render(request, 'recognition/index.html', {'active_tab': 'Explore'})

def modelinfo(request):
    """Model Info page (same dashboard, Model Info tab active)."""
    return render(request, 'recognition/index.html', {'active_tab': 'ModelInfo'})

def settings(request):
    """Settings page (same dashboard, Settings tab active)."""
    return render(request, 'recognition/index.html', {'active_tab': 'Settings'})

def login_page(request):
    """Authenticate a user with a normal Django session."""
    if request.user.is_authenticated:
        return redirect('recognition:recognize')

    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = None
        if email:
            username = User.objects.filter(email__iexact=email).values_list('username', flat=True).first()
            if username:
                user = authenticate(request, username=username, password=password)
        if user is None:
            error = 'Invalid email address or password.'
        else:
            login(request, user)
            return redirect('recognition:recognize')

    return render(request, 'recognition/login.html', {'error': error})


def register_page(request):
    """Create a Django user and start an authenticated session."""
    if request.user.is_authenticated:
        return redirect('recognition:recognize')

    values = {
        'full_name': request.POST.get('full_name', '').strip(),
        'email': request.POST.get('email', '').strip(),
    }
    errors = []
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        full_name = values['full_name']
        email = values['email']

        if not full_name:
            errors.append('Please enter your full name.')
        if not email:
            errors.append('Please enter your email address.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append('Please enter a valid email address.')
        if User.objects.filter(email__iexact=email).exists():
            errors.append('An account with this email already exists.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        if not errors:
            name_parts = full_name.split(None, 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''
            username_base = ''.join(char for char in email.split('@', 1)[0].lower() if char.isalnum() or char in '._-') or 'user'
            username = username_base
            suffix = 1
            while User.objects.filter(username=username).exists():
                suffix += 1
                username = f'{username_base}{suffix}'
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            UserPreference.objects.get_or_create(user=user)
            login(request, user)
            return redirect('recognition:recognize')

    return render(request, 'recognition/register.html', {'errors': errors, 'values': values})


@login_required
def account(request):
    """Show only the authenticated user's account information."""
    return render(request, 'recognition/account.html', {'account_user': request.user})


def logout_page(request):
    """Invalidate the Django session and return to the sign-in page."""
    logout(request)
    return redirect('recognition:login')

