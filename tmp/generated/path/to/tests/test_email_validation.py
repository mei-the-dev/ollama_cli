# Import the necessary module
import pytest
from email_validator import validate_email, EmailNotValidError

def is_valid_email(s):
    try:
        # Validate the email using the email_validator library
        validate_email(s)
        return True
    except EmailNotValidError:
        return False

def test_is_valid_email():
    # Test with a valid email address
    assert is_valid_email('test@example.com') == True, 'Should be valid'
    
    # Test with an invalid email address (missing @)
    assert is_valid_email('invalidemail.com') == False, 'Should be invalid'
    
    # Test with an empty string
    assert is_valid_email('') == False, 'Empty string should be invalid'
    
    # Test with a very long email address (edge case)
    long_email = 'a' * 254 + '@example.com'
    assert is_valid_email(long_email) == True, 'Long but valid email should pass'
    
    # Test with an invalid domain
    assert is_valid_email('test@.com') == False, 'Invalid domain should be invalid'
    
    # Test with a local part that starts with a dot
    assert is_valid_email('.test@example.com') == False, 'Local part starting with dot should be invalid'
    
    # Test with a local part that ends with a dot
    assert is_valid_email('test.@example.com') == False, 'Local part ending with dot should be invalid'
    
    # Test with an email containing special characters in the local part
    assert is_valid_email('test+special@char.example.com') == True, 'Email with special chars in local part should pass'