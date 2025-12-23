# test_is_valid_email.py
import pytest
from some_module import is_valid_email

def test_is_valid_email_basic():
    # Basic valid email
    assert is_valid_email('test@example.com') == True

def test_is_valid_email_with_subdomain():
    # Email with subdomain
    assert is_valid_email('user@mail.example.com') == True

def test_is_valid_email_long_tld():
    # Email with long top-level domain
    assert is_valid_email('test@example.co.uk') == True

def test_is_valid_email_invalid_characters():
    # Invalid characters in local part
    assert is_valid_email('invalid-email@domain.com') == False

def test_is_valid_email_missing_at_symbol():
    # Missing '@' symbol
    assert is_valid_email('missingatdomain.com') == False

def test_is_valid_email_empty_string():
    # Empty string
    assert is_valid_email('') == False

def test_is_valid_email_only_local_part():
    # Only local part, no domain
    assert is_valid_email('localpart@') == False

def test_is_valid_email_numeric_domain():
    # Numeric domain
    assert is_valid_email('test@123.com') == True

def test_is_valid_email_long_local_part():
    # Long local part
    assert is_valid_email('verylonglocalpartthatexceedsthesixtyfourcharacterlimit@domain.com') == False

def test_is_valid_email_special_characters():
    # Special characters in domain
    assert is_valid_email('test@domain-with-hyphen.com') == True

def test_is_valid_email_unicode_domain():
    # Unicode domain
    assert is_valid_email('test@xn--fsq.com') == True
