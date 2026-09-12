"""Route smoke test: every page route + full API flow (idempotent, self-cleaning)."""
import json, logging, os
logging.disable(logging.CRITICAL)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'image_recognition.settings')
import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from recognition.models import PredictionHistory, UserPreference

User.objects.filter(username__in=['alice', 'alice2', 'bob']).delete()

FAILURES = []
def check(label, cond, detail=""):
    if not cond:
        FAILURES.append(label)
    print(f"[{'PASS' if cond else 'FAIL'}] {label} {detail}")

def post(path, payload, client=None):
    return (client or Client()).post(path, json.dumps(payload), content_type='application/json')

c = Client()

print("=== PAGE ROUTES (anonymous) ===")
for url in ['/', '/history/', '/explore/', '/modelinfo/', '/settings/']:
    r = c.get(url)
    check(f"page {url} (anon)", r.status_code == 200, f"-> {r.status_code}")
check("/login/ renders sign-in page", c.get('/login/').status_code == 200)

print("\n=== PROTECTED API (anonymous) ===")
check("GET /api/settings/ anon -> 401", c.get('/api/settings/').status_code == 401)
check("POST /api/settings/ anon -> 401", c.post('/api/settings/', '{}', content_type='application/json').status_code == 401)

print("\n=== SIGNUP VALIDATION ===")
r = post('/api/signup/', {'username': 'alice', 'email': 'not-an-email', 'password': 'Passw0rd123', 'confirm_password': 'Passw0rd123'})
check("invalid email rejected", r.status_code == 400 and 'valid email' in r.json().get('error', ''), f"-> {r.json().get('error','')}")
r = post('/api/signup/', {'username': 'alice', 'email': 'a@b.com', 'password': 'short', 'confirm_password': 'short'})
check("weak password rejected", r.status_code == 400 and '8 characters' in r.json().get('error', ''), f"-> {r.json().get('error','')}")
r = post('/api/signup/', {'username': 'alice', 'email': 'a@b.com', 'password': 'Passw0rd123', 'confirm_password': 'Different123'})
check("password mismatch rejected", r.status_code == 400 and 'not match' in r.json().get('error', ''), f"-> {r.json().get('error','')}")
r = post('/api/signup/', {'username': '', 'email': 'a@b.com', 'password': 'Passw0rd123', 'confirm_password': 'Passw0rd123'})
check("empty username rejected", r.status_code == 400, f"-> {r.json().get('error','')}")
r = post('/api/signup/', {'username': 'alice', 'email': 'a@b.com', 'password': 'Passw0rd123', 'confirm_password': 'Passw0rd123'})
check("valid signup succeeds", r.status_code == 200 and r.json().get('success') is True, f"-> {r.status_code}")
u = User.objects.get(username='alice')
check("password stored hashed (pbkdf2)", u.password.startswith('pbkdf2_') and 'Passw0rd123' not in u.password)
check("UserPreference auto-created", UserPreference.objects.filter(user=u).exists())

print("\n=== LOGIN VALIDATION ===")
r = post('/api/login/', {'username': 'alice', 'password': 'WrongPass123'})
check("wrong credentials rejected", r.status_code == 400 and 'Invalid username or password' in r.json().get('error', ''))
c2 = Client()
r = post('/api/login/', {'username': 'alice', 'password': 'Passw0rd123'}, client=c2)
check("correct login succeeds", r.status_code == 200 and r.json().get('success') is True)

print("\n=== DUPLICATE REGISTRATION ===")
r = post('/api/signup/', {'username': 'alice', 'email': 'x@y.com', 'password': 'Passw0rd123', 'confirm_password': 'Passw0rd123'})
check("duplicate username rejected", r.status_code == 400 and 'already taken' in r.json().get('error', ''))
r = post('/api/signup/', {'username': 'alice2', 'email': 'a@b.com', 'password': 'Passw0rd123', 'confirm_password': 'Passw0rd123'})
check("duplicate email rejected", r.status_code == 400 and 'already exists' in r.json().get('error', ''), f"-> {r.json().get('error','')}")

print("PART1_DONE")

print("\n=== SETTINGS SAVE & PERSIST ===")
r = post('/api/settings/', {'email': 'newalice@b.com', 'auto_save_history': False}, client=c2)
check("POST /api/settings/ ok", r.status_code == 200)
check("email updated in DB", User.objects.get(username='alice').email == 'newalice@b.com')
check("auto_save_history persisted", UserPreference.objects.get(user=u).auto_save_history is False)
data = c2.get('/api/settings/').json()
check("GET /api/settings/ reflects save", data.get('auto_save_history') is False and data.get('email') == 'newalice@b.com')

print("\n=== PREDICT API (input validation only, no model load) ===")
from django.core.files.uploadedfile import SimpleUploadedFile
r = c2.post('/api/predict/')
check("missing image -> 400", r.status_code == 400, f"-> {r.json().get('error','')}")
r = c2.post('/api/predict/', {'image': SimpleUploadedFile('x.exe', b'xx')})
check("invalid file type -> 400", r.status_code == 400, f"-> {r.json().get('error','')}")

print("\n=== HISTORY: SAVE, ISOLATION, DELETE ===")
PredictionHistory.objects.create(user=u, image_name='cat.jpg', class_name='Egyptian Cat', subtitle='Animal: Egyptian Cat', confidence='92%', tag='Animal', description='test row for alice')
bob = User.objects.create_user(username='bob', email='bob@b.com', password='BobPass123')
UserPreference.objects.create(user=bob)
PredictionHistory.objects.create(user=bob, image_name='car.jpg', class_name='Sports Car', subtitle='Vehicle: Sports Car', confidence='88%', tag='Vehicle', description='test row for bob')
c3 = Client()
post('/api/login/', {'username': 'bob', 'password': 'BobPass123'}, client=c3)
alice_items = c2.get('/api/history/').json()['history']
bob_items = c3.get('/api/history/').json()['history']
check("alice sees only her history", len(alice_items) == 1 and alice_items[0]['class_name'] == 'Egyptian Cat', f"-> {len(alice_items)} item(s)")
check("bob sees only his history", len(bob_items) == 1 and bob_items[0]['class_name'] == 'Sports Car', f"-> {len(bob_items)} item(s)")
check("no cross-user leakage", all(i['class_name'] != 'Sports Car' for i in alice_items) and all(i['class_name'] != 'Egyptian Cat' for i in bob_items))
r = c3.delete('/api/history/')
check("bob clears his history", r.status_code == 200 and len(c3.get('/api/history/').json()['history']) == 0)
check("alice's history untouched", len(c2.get('/api/history/').json()['history']) == 1)

print("\n=== PAGE ROUTES (authenticated) ===")
for url in ['/', '/history/', '/explore/', '/modelinfo/', '/settings/']:
    r = c2.get(url)
    check(f"page {url} (auth)", r.status_code == 200, f"-> {r.status_code}")

print("\n=== LOGOUT ===")
r = c2.post('/api/logout/')
check("logout ok", r.status_code == 200)
check("session invalidated", c2.get('/api/me/').json().get('authenticated') is False)

print("\n=== CLEANUP TEST DATA ===")
User.objects.filter(username__in=['alice', 'alice2', 'bob']).delete()
check("test users removed", not User.objects.filter(username__in=['alice', 'alice2', 'bob']).exists())

print("\n" + ("ALL TESTS PASSED" if not FAILURES else f"FAILURES: {FAILURES}"))
