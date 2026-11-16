from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_defaults_to_legal_reviewer(self):
        user = User.objects.create_user(email="rev@example.com", password="pw12345!")
        self.assertEqual(user.role, User.Role.LEGAL_REVIEWER)
        self.assertFalse(user.is_admin)
        self.assertTrue(user.check_password("pw12345!"))
        self.assertFalse(user.is_staff)

    def test_create_superuser_is_admin(self):
        admin = User.objects.create_superuser(email="root@example.com", password="pw12345!")
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_no_username_field(self):
        self.assertFalse(hasattr(User, "username"))
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pw12345!")

    def test_str_is_email(self):
        user = User.objects.create_user(email="str@example.com", password="pw12345!")
        self.assertEqual(str(user), "str@example.com")
