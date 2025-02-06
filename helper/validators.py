import re
from rest_framework.exceptions import ValidationError

def valid_email(user_email):
    expression = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if not re.match(expression,user_email):
        return ValidationError("This field must be an even number.")
    else:
        return True
