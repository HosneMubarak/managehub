from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from faker import Faker
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create 10 dummy users for testing'

    def handle(self, *args, **options):
        fake = Faker()
        
        # Create 10 dummy users
        users_created = 0
        
        for i in range(10):
            # Generate unique username and email
            username = fake.user_name()
            email = fake.email()
            
            # Ensure uniqueness
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            
            counter = 1
            original_email = email
            while User.objects.filter(email=email).exists():
                email_parts = original_email.split('@')
                email = f"{email_parts[0]}{counter}@{email_parts[1]}"
                counter += 1
            
            # Create user with correct fields based on the actual User model
            user = User.objects.create_user(
                username=username,
                email=email,
                password='testpass123',
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone_number=fake.phone_number(),
                gender=random.choice([choice[0] for choice in User.Gender.choices]),
                occupation=random.choice([choice[0] for choice in User.Occupation.choices]),
                bio=fake.text(max_nb_chars=200),
                country=random.choice(['US', 'CA', 'GB', 'AU', 'DE', 'FR']),
                city_of_origin=fake.city(),
                is_active=True
            )
            
            users_created += 1
            self.stdout.write(
                self.style.SUCCESS(f'Created user: {user.username} ({user.email})')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {users_created} dummy users')
        )
