import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema_booking.settings')
django.setup()

from django.contrib.auth.models import User

username = 'admin'
email = 'admin@example.com'
password = 'admin'

if not User.objects.filter(username=username).exists():
    print(f"Creating superuser '{username}'...")
    User.objects.create_superuser(username, email, password)
    print(f"Superuser '{username}' created successfully!")
    print(f"Username: {username}")
    print(f"Password: {password}")
else:
    print(f"Superuser '{username}' already exists.")
    user = User.objects.get(username=username)
    if not user.is_superuser:
        print(f"User '{username}' is not a superuser. Making them one...")
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f"User '{username}' is now a superuser.")
    else:
        print(f"User '{username}' is already a superuser.")
