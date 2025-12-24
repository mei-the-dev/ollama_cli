# test_is_valid_email.py
import pytest
from your_module import is_valid_email


def test_is_valid_email_basic():
    # Basic valid email
    assert is_valid_email("test@example.com") == True


def test_is_valid_email_with_subdomain():
    # Email with subdomain
    assert is_valid_email("user@mail.example.com") == True


def test_is_valid_email_long_tld():
    # Email with long TLD
    assert is_valid_email("test@example.toolongtld") == False


def test_is_valid_email_no_at_symbol():
    # Missing '@' symbol
    assert is_valid_email("testexample.com") == False


def test_is_valid_email_empty_local_part():
    # Empty local part before '@'
    assert is_valid_email("@example.com") == False


def test_is_valid_email_empty_domain_part():
    # Empty domain part after '@'
    assert is_valid_email("test@.com") == False


def test_is_valid_email_invalid_characters():
    # Invalid characters in local part
    assert is_valid_email("test!@example.com") == False


def test_is_valid_email_long_local_part():
    # Long local part (64 characters)
    long_local = "a" * 64 + "@example.com"
    assert is_valid_email(long_local) == True


def test_is_valid_email_long_domain_part():
    # Long domain part (253 characters)
    long_domain = "a" * 63 + "." + "b" * 17 + ".com"
    assert is_valid_email("test@" + long_domain) == True


def test_is_valid_email_long_combined():
    # Long combined local and domain parts (254 characters)
    long_local = "a" * 63
    long_domain = "b" * 17 + ".com"
    assert is_valid_email(long_local + "@" + long_domain) == True


def test_is_valid_email_ip_address():
    # Valid email with IP address domain
    assert is_valid_email("test@[192.168.0.1]") == True


def test_is_valid_email_ipv6_address():
    # Valid email with IPv6 address domain
    ipv6 = "test@[2001:db8::1]"
    assert is_valid_email(ipv6) == True
