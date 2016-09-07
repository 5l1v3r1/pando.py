"""
pando.website
+++++++++++++
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import os

from algorithm import Algorithm
from aspen.configuration import configure, parse
from aspen.request_processor import KNOBS as ASPEN_KNOBS, RequestProcessor

from . import body_parsers
from .http.response import Response
from .utils import to_rfc822, utc
from .exceptions import BadLocation

# 2006-11-17 was the first release of pando - v0.3
THE_PAST = to_rfc822(datetime.datetime(2006, 11, 17, tzinfo=utc))


KNOBS = {
    # 'name':               (default,               from_unicode),
    'base_url':             ('',                    parse.identity),
    'list_directories':     (False,                 parse.yes_no),
    'logging_threshold':    (0,                     int),
    'show_tracebacks':      (False,                 parse.yes_no),
    'colorize_tracebacks':  (True,                  parse.yes_no),
}


class Website(object):
    """Represent a website.

    This object holds configuration information, and how to handle HTTP
    requests (per WSGI). It is available to user-developers inside of their
    simplates and algorithm functions.

    """

    def __init__(self, **kwargs):
        """Takes configuration in kwargs.
        """
        self.request_processor = RequestProcessor(**kwargs)
        aspen_algo = self.request_processor.algorithm
        pando_algo = Algorithm.from_dotted_name('pando.algorithms.website')
        pando_algo.insert_before(
            'handle_dispatch_exception',
            aspen_algo['dispatch_path_to_filesystem'],
        )
        pando_algo.insert_before(
            'resource_available',
            aspen_algo['apply_typecasters_to_path'],
            aspen_algo['load_resource_from_filesystem'],
        )
        pando_algo.insert_before(
            'fill_response_with_output',
            aspen_algo['render_resource'],
        )
        self.algorithm = pando_algo
        self.configure(**kwargs)

    def configure(self, **kwargs):
        # copy aspen's config variables, for backward compatibility
        extra = 'typecasters renderer_factories default_renderers_by_media_type'
        for key in list(ASPEN_KNOBS) + extra.split():
            self.__dict__[key] = self.request_processor.__dict__[key]

        # load our own config variables
        configure(KNOBS, self.__dict__, 'PANDO_', kwargs)

        # add ourself to the initial context of simplates
        self.request_processor.simplate_defaults.initial_context['website'] = self

        # load bodyparsers
        self.body_parsers = {
            "application/x-www-form-urlencoded": body_parsers.formdata,
            "multipart/form-data": body_parsers.formdata,
            self.media_type_json: body_parsers.jsondata
        }


    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def wsgi_app(self, environ, start_response):
        """WSGI interface.

        Wrap this method (instead of the website object itself) when you want
        to use WSGI middleware::

            website = Website()
            website.wsgi_app = WSGIMiddleware(website.wsgi_app)

        """
        wsgi = self.respond(environ)['response']
        return wsgi(environ, start_response)


    def respond(self, environ, raise_immediately=None, return_after=None):
        """Given a WSGI environ, return a state dict.
        """
        return self.algorithm.run( website=self
                                 , environ=environ
                                 , _raise_immediately=raise_immediately
                                 , _return_after=return_after
                                  )

    def redirect(self, location, code=None, permanent=False, base_url=None, response=None):
        """Raise a redirect Response.

        If code is None then it will be set to 301 (Moved Permanently) if
        permanent is True and 302 (Found) if it is False. If url doesn't start
        with base_url (defaulting to self.base_url), then we prefix it with
        base_url before redirecting. This is a protection against open
        redirects. If you wish to use a relative path or full URL as location,
        then base_url must be the empty string; if it's not, we raise
        BadLocation. If you provide your own response we will set .code and
        .headers['Location'] on it.

        """
        response = response if response else Response()
        response.code = code if code else (301 if permanent else 302)
        base_url = base_url if base_url is not None else self.base_url
        if not location.startswith(base_url):
            newloc = base_url + location
            if not location.startswith('/'):
                raise BadLocation(newloc)
            location = newloc
        response.headers[b'Location'] = location.encode('ascii')
        raise response


    # Base URL Canonicalization
    # =========================

    def _extract_scheme(self, request):
        return request.headers.get(b'X-Forwarded-Proto', b'http')  # Heroku

    def _extract_host(self, request):
        return request.headers[b'Host']  # will 400 if missing

    _canonicalize_base_url_code = 302

    def canonicalize_base_url(self, request):
        """Enforces a base_url such as http://localhost:8080 (no path part).
        """
        if not self.base_url:
            return

        scheme = self._extract_scheme(request).decode('ascii', 'repr')
        host = self._extract_host(request).decode('ascii', 'repr')

        actual = scheme + "://" + host

        if actual != self.base_url:
            url = self.base_url
            if request.line.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
                # Redirect to a particular path for idempotent methods.
                url += request.line.uri.path.raw
                if request.line.uri.querystring:
                    url += '?' + request.line.uri.querystring.raw
            else:
                # For non-idempotent methods, redirect to homepage.
                url += '/'
            self.redirect(url, code=self._canonicalize_base_url_code)


    # File Resolution
    # ===============

    def find_ours(self, filename):
        """Given a filename, return the filepath to pando's internal version
        of that filename.  No existence checking is done, this just abstracts
        away the __file__ reference nastiness.
        """
        return os.path.join(os.path.dirname(__file__), 'www', filename)

    def ours_or_theirs(self, filename):
        """Given a filename, return a filepath or None.
        """
        if self.project_root is not None:
            theirs = os.path.join(self.project_root, filename)
            if os.path.isfile(theirs):
                return theirs

        ours = self.find_ours(filename)
        if os.path.isfile(ours):
            return ours

        return None