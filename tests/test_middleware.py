from django.http import HttpResponse
from django.test import RequestFactory
from django.test.utils import override_settings
from django.core.exceptions import ImproperlyConfigured

from django_hosts.middleware import (HostsRequestMiddleware,
                                     HostsResponseMiddleware)

from .base import HostsTestCase


class MiddlewareTests(HostsTestCase):

    def test_missing_hostconf_setting(self):
        self.assertRaisesMessage(ImproperlyConfigured,
            'Missing ROOT_HOSTCONF setting', HostsRequestMiddleware)

    @override_settings(ROOT_HOSTCONF='tests.hosts.simple')
    def test_missing_default_hosts(self):
        self.assertRaisesMessage(ImproperlyConfigured,
            'Missing DEFAULT_HOST setting', HostsRequestMiddleware)

    @override_settings(
        ROOT_HOSTCONF='tests.hosts.simple',
        DEFAULT_HOST='boo')
    def test_wrong_default_hosts(self):
        self.assertRaisesMessage(ImproperlyConfigured,
            "Invalid DEFAULT_HOST setting: No host called 'boo' exists",
            HostsRequestMiddleware)

    @override_settings(
        ALLOWED_HOSTS=['other.example.com'],
        ROOT_HOSTCONF='tests.hosts.simple',
        DEFAULT_HOST='www')
    def test_request_urlconf_module(self):
        rf = RequestFactory(HTTP_HOST='other.example.com')
        request = rf.get('/simple/')
        middleware = HostsRequestMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'tests.urls.simple')
        
    @override_settings(
        ALLOWED_HOSTS=['example.com'],
        ROOT_HOSTCONF='tests.hosts.blank_wildcard',
        PARENT_HOST='example.com',
        DEFAULT_HOST='root')
    def test_request_blank_urlconf_module(self):
        rf = RequestFactory(HTTP_HOST='example.com')
        request = rf.get('/')
        middleware = HostsRequestMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'tests.urls.root')

    @override_settings(
        ALLOWED_HOSTS=['other.example.com'],
        ROOT_HOSTCONF='tests.hosts.simple',
        DEFAULT_HOST='www')
    def test_response_urlconf_module(self):
        rf = RequestFactory(HTTP_HOST='other.example.com')
        request = rf.get('/simple/')
        middleware = HostsResponseMiddleware()
        middleware.process_response(request, HttpResponse('test'))
        self.assertEqual(request.urlconf, 'tests.urls.simple')

    @override_settings(
        ALLOWED_HOSTS=['ss.example.com'],
        ROOT_HOSTCONF='tests.hosts.simple',
        DEFAULT_HOST='with_view_kwargs')
    def test_fallback_to_defaulthost(self):
        rf = RequestFactory(HTTP_HOST='ss.example.com')
        request = rf.get('/template/test/')
        middleware = HostsRequestMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'tests.urls.complex')
        host, kwargs = middleware.get_host('non-existing')
        self.assertEqual(host.name, 'with_view_kwargs')

    @override_settings(
        ROOT_HOSTCONF='tests.hosts.simple',
        DEFAULT_HOST='www',
        MIDDLEWARE=[
            'django_hosts.middleware.HostsRequestMiddleware',
            'django_hosts.middleware.HostsResponseMiddleware',
        ])
    def test_request(self):
        # This does a pass through the middleware and ensures that the
        # middleware's __init__() assigns the get_response attribute.
        response = self.client.get('/')
        self.assertEqual(response.status_code, 404)

    @override_settings(
        ROOT_HOSTCONF='tests.hosts.simple',
        DEFAULT_HOST='www',
        ALLOWED_HOSTS=['somehost.com'],
        DEBUG=False,
        MIDDLEWARE=[
            'django_hosts.middleware.HostsRequestMiddleware',
            'django_hosts.middleware.HostsResponseMiddleware',
        ])
    def test_fallback_with_evil_host(self):
        response = self.client.get('/', HTTP_HOST='evil.com')
        self.assertEqual(response.status_code, 400)

    @override_settings(
        ALLOWED_HOSTS=['spam.eggs.example.com'],
        ROOT_HOSTCONF='tests.hosts.multiple',
        DEFAULT_HOST='multiple')
    def test_multiple_subdomains(self):
        rf = RequestFactory(HTTP_HOST='spam.eggs.example.com')
        request = rf.get('/multiple/')
        middleware = HostsRequestMiddleware()
        middleware.process_request(request)
        self.assertEqual(request.urlconf, 'tests.urls.multiple')

    @override_settings(
        MIDDLEWARE=[
            'debug_toolbar.middleware.DebugToolbarMiddleware',
            'django_hosts.middleware.HostsRequestMiddleware'
        ],
        ROOT_HOSTCONF='tests.hosts.multiple',
        DEFAULT_HOST='multiple')
    def test_debug_toolbar_new_warning(self):
        msg = (
            'The django-hosts and django-debug-toolbar middlewares are in the '
            'wrong order. Make sure the django-hosts middleware comes before '
            'the django-debug-toolbar middleware in the MIDDLEWARE setting.'
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            HostsRequestMiddleware()
