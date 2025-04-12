# Standard library imports
import csv
import json
import uuid
import hashlib
from datetime import datetime
from functools import wraps
from pathlib import Path

# Third-party imports
import jwt
from cryptography.hazmat.primitives import serialization

# Django imports
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

# Local application imports
from credentials.models import CustomUser
from enrollments.models import Enrollment


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

@require_GET
@login_required
@approved_required
def enrollments_view(request):
    """
    Render the enrollment page.
    """
    enrollments = Enrollment.objects.all()
    all_keys = set()
    for enrollment in enrollments:
        all_keys.update(enrollment.data.keys())

    all_keys.discard("timestamp")
    all_keys.discard("nonce")
    all_keys = sorted(all_keys, key=lambda x: (x != "user", x))

    return render(request, 'enrollments.html', {
        'enrollments': enrollments,
        'all_enrollment_keys': all_keys
    })

@require_GET
@login_required
@approved_required
def csv_view(request):
    """
    Render the CSV page with dynamic fields.
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8',
                            headers={'Content-Disposition': 'attachment; filename="enrollment_data.csv"'})
    writer = csv.writer(response)

    # Get all unique keys from the data field
    enrollments = Enrollment.objects.all()
    keys = set()
    for enrollment in enrollments:
        keys.update(enrollment.data.keys())

    keys.discard("timestamp")
    keys.discard("nonce")
    keys = sorted(keys, key=lambda x: (x != "user", x))

    # Write the header row
    writer.writerow(['Enrollment ID'] + list(keys) + ['Timestamp'])

    # Write the data rows
    for enrollment in enrollments:
        row = [enrollment.id]
        for key in keys:
            row.append(enrollment.data.get(key, ''))  # Use empty string if key is missing
        row.append(enrollment.timestamp)
        writer.writerow(row)

    return response

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

        # Store the entire payload dynamically
        enrollment = Enrollment.objects.create(data=data)

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