# Standard library imports
import json
import uuid
import hashlib
import requests
from datetime import datetime
from functools import wraps
from pathlib import Path
import random
import string

# Third-party imports
import jwt
from cryptography.hazmat.primitives import serialization

# Django imports
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

# Local application imports
from credentials.models import CustomUser
from enrollments.models import Enrollment, Profile, Badge, UserBadge


PUBLIC_KEY = serialization.load_pem_public_key(open(settings.HOME + ('/' if settings.HOME else '') + 'public_key.pem', 'rb').read())

@require_GET
def home_view(request):
    """
    Render the home page.
    """
    return render(request, 'home.html')

def approved_required(view_func):
    """
    Decorator to check if the user is approved.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_approved:
            return view_func(request, *args, **kwargs)
        else:
            return render(request, 'home.html')
    return _wrapped_view

@login_required
@approved_required
def proxy_api_request(request):
    """
    Proxy API request to the external service.
    """
    if request.method == 'GET':
        query = request.GET.get('query', '')
        items = request.GET.get('item', '')
        if not query and not items:
            return JsonResponse({'error': 'Query or item parameter is required'}, status=400)

        if query:
            api_url = f"https://capx-backend.toolforge.org/users/?{query}"
            response = requests.get(api_url)
        elif items:
            api_url = f"https://capx-backend.toolforge.org/list/{items}/"
            response = requests.get(api_url)

        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': 'Failed to fetch data from external service'}, status=response.status_code)
    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
            qids = body.get('qids', [])
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if not qids:
            return JsonResponse({'error': 'QIDs parameter is required'}, status=400)

        # Construct SPARQL query
        mb_query_text = f"""PREFIX wbt:<https://metabase.wikibase.cloud/prop/direct/>  
            SELECT ?item ?itemLabel ?value WHERE {{  
                VALUES ?value {{{" ".join([f'"{qid}"' for qid in qids])}}}  
                ?item wbt:P67/wbt:P1 ?value.  
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language 'en'. }}
            }}
        """
        
        api_url = "https://metabase.wikibase.cloud/query/sparql"
        response = requests.post(
            api_url,
            data={"query": mb_query_text},
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "CapX/1.0",
            },
        )

        if response.status_code == 200:
            # Process the raw results to a consistent format
            raw_results = response.json().get("results", {}).get("bindings", [])
            results = [
                {
                    "wd_code": item.get("value", {}).get("value"),
                    "name": item.get("itemLabel", {}).get("value"),
                    "item": item.get("item", {}).get("value"),
                }
                for item in raw_results
                if item.get("item") and item.get("itemLabel") and item.get("value")
            ]
            return JsonResponse(results, safe=False)
        else:
            return JsonResponse({'error': 'Failed to fetch data from external service'}, status=response.status_code)

@require_GET
@login_required
@approved_required
def enrollments_view(request):
    """
    Render the enrollment page.
    """
    enrollments = list(Enrollment.objects.all())
    all_keys = set()
    for enrollment in enrollments:
        all_keys.update(enrollment.data.keys())

    all_keys.discard("timestamp")
    all_keys.discard("nonce")
    all_keys.add("legacy")
    all_keys = sorted(all_keys, key=lambda x: (x != "user", x))

    user_names = Enrollment.objects.values_list('user', flat=True)
    profiles = Profile.objects.exclude(username__in=user_names)

    for profile in profiles:
        enrollments.append({
            "user": profile.username,
            "data": {
                "user": profile.username,
                "email": profile.email,
                "full_name": profile.full_name,
            },
        })

    legacy_users = set(Profile.objects.values_list('username', flat=True))
    for i, enrollment in enumerate(enrollments):
        if isinstance(enrollment, Enrollment):
            enrollment.data["legacy"] = True if enrollment.user in legacy_users else False
        elif isinstance(enrollment, dict):
            enrollment["data"]["legacy"] = True if enrollment["user"] in legacy_users else False

    return render(request, 'enrollments.html', {
        'enrollments': enrollments,
        'all_enrollment_keys': all_keys
    })

@login_required
@approved_required
def manage_view(request):
    """
    Render the manage page.
    """
    unapproved_users = CustomUser.objects.filter(is_approved=False)
    approved_users = CustomUser.objects.filter(is_approved=True).exclude(id=request.user.id)  # Exclude the current user

    if request.method == 'POST':
        action = request.POST.get('action')
        username = request.POST.get('username')

        if not username:
            return render(request, 'manage.html', {
                'unapproved_users': unapproved_users,
                'approved_users': approved_users,
                'error': 'Username is required'
            })

        try:
            user = CustomUser.objects.get(username=username)
            if action == 'approve':
                user.is_approved = True
                user.save()
                success_message = f"User '{username}' has been approved."
            elif action == 'unapprove':
                user.is_approved = False
                user.save()
                success_message = f"User '{username}' has been unapproved."
            else:
                success_message = None

            return render(request, 'manage.html', {
                'unapproved_users': unapproved_users,
                'approved_users': approved_users,
                'success': success_message
            })
        except CustomUser.DoesNotExist:
            return render(request, 'manage.html', {
                'unapproved_users': unapproved_users,
                'approved_users': approved_users,
                'error': f"User '{username}' not found."
            })

    return render(request, 'manage.html', {
        'unapproved_users': unapproved_users,
        'approved_users': approved_users
    })

@require_GET
def profile_view(request):
    """
    View to retrieve and display user profile information.
    """
    username = request.GET.get('username')
    if not username:
        return JsonResponse({'error': 'Username parameter is required'}, status=400)

    profile = get_object_or_404(Profile, username=username)
    return JsonResponse({
        'username': profile.username,
        'username_org': profile.username_org,
        'reconciled_affiliation': profile.reconciled_affiliation,
        'reconciled_territory': profile.reconciled_territory,
        'reconciled_languages': profile.reconciled_languages,
        'reconciled_projects': profile.reconciled_projects,
        'reconciled_want_to_learn': profile.reconciled_want_to_learn,
        'reconciled_want_to_share': profile.reconciled_want_to_share
    })

@require_GET
def exist_view(request):
    """
    View to check if a user exists.
    """
    username = request.GET.get('username')
    if not username:
        return JsonResponse({'error': 'Username parameter is required'}, status=400)

    exists = Profile.objects.filter(username=username).exists()
    return JsonResponse({'exists': exists})


@require_GET
def user_badges_api(request):
    """
    Public API: GET /user-badges/?username=<name>
    Returns a list of badges awarded to the given username.
    Each item: { name, picture, description, timestamp, verification_code }
    """
    username = request.GET.get('username')
    if not username:
        return JsonResponse({'error': 'Username parameter is required'}, status=400)

    userbadges = (
        UserBadge.objects.filter(user=username)
        .select_related('badge')
        .order_by('-issued_at')
    )

    results = [
        {
            'name': ub.badge.name,
            'picture': ub.badge.image,
            'description': ub.badge.description,
            'timestamp': ub.issued_at.isoformat(),
            'verification_code': ub.verification_code,
        }
        for ub in userbadges
    ]

    return JsonResponse(results, safe=False)


@require_GET
def badge_verification_view(request, verification_code: str):
    """
    Public page: GET /badge/<verification_code>/
    Renders a certificate-like page with badge, user, and issuance info.
    """
    userbadge = get_object_or_404(UserBadge.objects.select_related('badge'), verification_code=verification_code)

    context = {
        'username': userbadge.user,
        'badge': userbadge.badge,
        'issued_at': userbadge.issued_at,
        'verification_code': userbadge.verification_code[-10:] if len(userbadge.verification_code) > 10 else userbadge.verification_code,
        'site_name': "Let's Connect",
        'site_logo': "https://upload.wikimedia.org/wikipedia/commons/4/4c/Let%27s_Connect_logo.svg",
        'brand_color': "#122d4c",
    }
    return render(request, 'badge_certificate.html', context)


@login_required
@approved_required
def badges_view(request):
    """
    Manage badges: list, create, edit, and manage awarded users.
    Actions (POST):
      - add_badge: name, description, image
      - edit_badge: badge_id, name, description, image
      - grant_badge: badge_id, username
      - revoke_badge: userbadge_id
    """
    message = None
    error = None

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_badge':
                name = request.POST.get('name', '').strip()
                description = request.POST.get('description', '').strip()
                image = request.POST.get('image', '').strip()
                if not name:
                    raise ValueError('Badge name is required')
                Badge.objects.create(name=name, description=description, image=image)
                message = f"Badge '{name}' created."

            elif action == 'edit_badge':
                badge_id = request.POST.get('badge_id')
                badge = get_object_or_404(Badge, id=badge_id)
                name = request.POST.get('name', '').strip()
                description = request.POST.get('description', '').strip()
                image = request.POST.get('image', '').strip()
                if not name:
                    raise ValueError('Badge name is required')
                badge.name = name
                badge.description = description
                badge.image = image
                badge.save()
                message = f"Badge '{name}' updated."

            elif action == 'grant_badge':
                badge_id = request.POST.get('badge_id')
                username = request.POST.get('username', '').strip()
                if not username:
                    raise ValueError('Username is required')
                badge = get_object_or_404(Badge, id=badge_id)
                # Ensure profile exists as our users are char usernames in Profile/Enrollment
                # This does not restrict to approved users; managers can award to any known username
                # Prevent duplicates via unique_together
                if not Profile.objects.filter(username=username).exists():
                    # allow awarding even if profile not present, as UserBadge.user is CharField
                    pass
                # Try to generate a unique verification_code
                for _ in range(20):
                    verification_code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                    if not UserBadge.objects.filter(verification_code=verification_code).exists():
                        break
                else:
                    raise ValueError('Could not generate a unique verification code after 20 attempts.')
                try:
                    UserBadge.objects.create(user=username, badge=badge, verification_code=verification_code)
                    message = f"Granted '{badge.name}' to {username}."
                except Exception as e:
                    error = str(e)

            elif action == 'revoke_badge':
                ub_id = request.POST.get('userbadge_id')
                userbadge = get_object_or_404(UserBadge, id=ub_id)
                userbadge.delete()
                message = 'Badge revoked.'

            elif action == 'delete_badge':
                badge_id = request.POST.get('badge_id')
                badge = get_object_or_404(Badge, id=badge_id)
                name = badge.name
                badge.delete()  # cascades to UserBadge
                message = f"Badge '{name}' deleted."

        except Exception as e:
            error = str(e)

    badges = Badge.objects.all().order_by('name')
    profiles = Profile.objects.all().order_by('username')
    # Build mapping of badge_id -> awarded list
    awarded = {
        b.id: list(UserBadge.objects.filter(badge=b).order_by('-issued_at'))
        for b in badges
    }

    return render(request, 'badges.html', {
        'badges': badges,
        'profiles': profiles,
        'awarded': awarded,
        'message': message,
        'error': error,
    })

@csrf_exempt
@require_POST
def receive_enrollment_data(request):
    """
    Handle the enrollment data submission with dynamic fields.
    """
    try:
        token = json.loads(request.body).get('token', None)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not token:
        return JsonResponse({'error': 'Token is required'}, status=400)

    try:
        data = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'])
        if not data:
            return JsonResponse({'error': 'Invalid token'}, status=401)

        # Store the entire payload dynamically, updating only non-empty fields
        user = data.get('user')
        try:
            enrollment = Enrollment.objects.get(user=user)
            # Only update fields in enrollment.data if the new value is not None, blank, or zero
            updated_data = enrollment.data.copy() if enrollment.data else {}
            for k, v in data.items():
                if v not in [None, '', 0, 'null']:
                    updated_data[k] = v
            enrollment.data = updated_data
            enrollment.save(update_fields=['data'])
        except Enrollment.DoesNotExist:
            enrollment = Enrollment.objects.create(user=user, data=data)

        # Generate confirmation token
        confirmation_id = str(uuid.uuid4())
        confirmation_code = hashlib.sha256(
            f"{enrollment.id}-{confirmation_id}".encode()
        ).hexdigest()

        # Store the confirmation code
        enrollment.confirmation_code = confirmation_code
        enrollment.save(update_fields=["confirmation_code"])

        return JsonResponse({
            'message': 'Enrollment data received successfully',
            'confirmation': confirmation_code
        }, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
