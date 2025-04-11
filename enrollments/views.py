from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from cryptography.hazmat.primitives import serialization
from django.contrib.auth.decorators import login_required
from functools import wraps
from pathlib import Path
from credentials.models import CustomUser
import jwt
import csv
from enrollments.models import Enrollment
from django.conf import settings


PUBLIC_KEY = serialization.load_pem_public_key(open(settings.HOME + '/public_key.pem', 'rb').read())

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
            return render(request, 'not_approved.html')
    return _wrapped_view

@require_GET
@login_required
@approved_required
def enrollments_view(request):
    """
    Render the enrollment page.
    """
    return render(request, 'enrollments.html')

@require_GET
@login_required
@approved_required
def csv_view(request):
    """
    Render the CSV page.
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8',
                            headers={'Content-Disposition': 'attachment; filename="enrollment_data.csv"'})
    writer = csv.writer(response)

    writer.writerow(['Username', 'Full Name', 'Email', 'Role', 'Area', 'Gender', 'Age', 'Timestamp'])

    enrollments = Enrollment.objects.all()
    for enrollment in enrollments:
        writer.writerow([enrollment.user.username, enrollment.full_name, enrollment.email,
                         enrollment.role, enrollment.area, enrollment.gender,
                         enrollment.age, enrollment.timestamp])
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
    Handle the enrollment data submission.
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    token = auth_header.split(' ')[1]
    try:
        decoded = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'])
        data = decoded.get('data', {})
        if not data:
            return JsonResponse({'error': 'Invalid token'}, status=401)

        # Process the enrollment data here
        enrollment = Enrollment.objects.create(
            user=data.get('user'),
            full_name=data.get('full_name'),
            email=data.get('email'),
            role=data.get('role'),
            area=data.get('area'),
            gender=data.get('gender'),
            age=data.get('age'),
            timestamp=data.get('timestamp')
        )
        
        # Generate confirmation token
        confirmation_id = str(uuid.uuid4())
        confirmation_code = hashlib.sha256(
            f"{enrollment.id}-{confirmation_id}".encode()
        ).hexdigest()

        # Optionally store the confirmation ID in the model (for reverse lookup/debug)
        enrollment.confirmation_code = confirmation_code
        enrollment.save(update_fields=["confirmation_code"])

        return JsonResponse({
            'message': 'Enrollment data received successfully',
            'confirmation': confirmation_code
        }, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)