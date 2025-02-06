from rest_framework.response import Response


class SmoothException(Exception):
    """Custom exception to handle errors."""
    def __init__(self, message, redirect_url = 'Not applicable', status_code=400):
        self.message = message
        self.redirect_url = redirect_url
        self.status_code = status_code
        super().__init__(message)


def custom_exception_handler(exc, context):
    """
    Custom exception handler to wrap all errors in a consistent format.
    """
    # Handle SmoothException directly
    if isinstance(exc, SmoothException):
        return Response(
            {"detail": exc.message, "redirect_url": exc.redirect_url},
            status=exc.status_code
        )
    
    from rest_framework.views import exception_handler
    
    # Let DRF handle other exceptions
    response = exception_handler(exc, context)
    
    if response is not None:
        response.data['status_code'] = response.status_code

    return response
