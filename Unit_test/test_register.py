# Import the registration page for password checks
from UI.ui.register_page import RegisterPage

# Test case 1: Check that a valid strong password is accepted
def test_valid_password():
    password = "StrongPass1!"
    assert RegisterPage.valid_password(password) is True


# Test case 2: Check that a password shorter than 8 characters is rejected
def test_password_too_short():
    password = "Ab1!"
    assert RegisterPage.valid_password(password) is False


# Test case 3: Check that a password without an uppercase letter is rejected
def test_password_without_uppercase():
    password = "strongpass1!"
    assert RegisterPage.valid_password(password) is False


# Test case 4: Check that a password without a lowercase letter is rejected
def test_password_without_lowercase():
    password = "STRONGPASS1!"
    assert RegisterPage.valid_password(password) is False


# Test case 5: Check that a password without a number is rejected
def test_password_without_number():
    password = "StrongPass!"
    assert RegisterPage.valid_password(password) is False


# Test case 6: Check that a password without a symbol is rejected
def test_password_without_symbol():
    password = "StrongPass1"
    assert RegisterPage.valid_password(password) is False


# Test case 7: Check that an empty password is rejected
def test_empty_password():
    password = ""
    assert RegisterPage.valid_password(password) is False


# Test case 8: Check that exactly 8 characters can still form a valid password
def test_minimum_valid_password_length():
    password = "Abcde1!x"
    assert len(password) == 8
    assert RegisterPage.valid_password(password) is True