"""
Test helpers shared across the app suites.

Staff-permission tests need a logged-in superuser. Writing the password as a
literal in each test file trips secret scanners on every push, so the password
is generated per run and never appears in source.
"""

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string


def login_as_staff(client, username='staff'):
    """
    Create a superuser and log `client` in as them.

    Returns the user. The password is random per call and is thrown away —
    nothing in the suite needs to know it.
    """
    password = get_random_string(24)
    user = get_user_model().objects.create_superuser(
        username=username,
        email=f'{username}@example.com',
        password=password,
    )
    logged_in = client.login(username=username, password=password)
    assert logged_in, f'Could not log in the test superuser {username!r}.'
    return user
