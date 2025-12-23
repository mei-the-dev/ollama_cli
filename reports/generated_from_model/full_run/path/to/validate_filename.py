# validate_filename.py

def validate_and_sanitize_filename(filename):
    # Import necessary libraries
    import re
    import os
    
    # Define a regular expression pattern for valid filenames
    # This pattern allows alphanumeric characters, underscores, and hyphens
    valid_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    # Check if the filename matches the valid pattern
    if not valid_pattern.match(filename):
        raise ValueError("Invalid characters in filename. Only alphanumeric characters, underscores, and hyphens are allowed.")
    
    # Sanitize the filename to prevent directory traversal attacks
    sanitized_filename = os.path.basename(filename)
    
    return sanitized_filename

# Example usage:
if __name__ == "__main__":
    try:
        user_input = input("Enter a filename: ")
        safe_filename = validate_and_sanitize_filename(user_input)
        print(f"Sanitized filename: {safe_filename}")
    except ValueError as e:
        print(e)
