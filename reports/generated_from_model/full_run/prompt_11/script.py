#!/usr/bin/env python3


def prompt_user_yes_no(prompt, default=True):
    """
    Prompts the user with a yes/no question and handles CTRL-C.

    Args:
        prompt (str): The question to ask the user.
        default (bool): The default value if the user presses Enter without input.

    Returns:
        bool: True if the user responds with 'y' or 'yes', False otherwise.
    """
    while True:
        try:
            response = input(prompt).strip().lower()
            if not response and default is not None:
                return default
            elif response in ("y", "yes"):
                return True
            elif response in ("n", "no"):
                return False
            else:
                print("Please respond with 'y' or 'n'.")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return default
