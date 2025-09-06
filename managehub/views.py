from django.shortcuts import render
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError, Http404
from django.core.exceptions import PermissionDenied

def bad_request(request, exception=None):
    """Custom 400 error handler"""
    return HttpResponseBadRequest(render(request, '400.html'))

def permission_denied(request, exception=None):
    """Custom 403 error handler"""
    return HttpResponseForbidden(render(request, '403.html'))

def page_not_found(request, exception=None):
    """Custom 404 error handler"""
    return HttpResponseNotFound(render(request, '404.html'))

def server_error(request):
    """Custom 500 error handler"""
    return HttpResponseServerError(render(request, '500.html'))

# Test views to verify error handlers (only for development)
def test_404_view(request):
    """Test view to trigger 404 error"""
    raise Http404("Test 404 error")

def test_403_view(request):
    """Test view to trigger 403 error"""
    raise PermissionDenied("Test 403 error")

def test_500_view(request):
    """Test view to trigger 500 error"""
    raise Exception("Test 500 error")
