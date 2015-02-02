from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from pytest import raises

from aspen.http.request import Headers
import aspen.body_parsers as parsers
from aspen.exceptions import MalformedBody, UnknownBodyType


FORMDATA = object()
WWWFORM = object()

def make_body(raw, headers=None, content_type=WWWFORM):
    if isinstance(raw, unicode):
        raw = raw.encode('ascii')
    if headers is None:
        defaults = { FORMDATA: "multipart/form-data; boundary=AaB03x",
                     WWWFORM: "application/x-www-form-urlencoded" }
        headers = {"Content-Type": defaults.get(content_type, content_type)}
    if not 'content-length' in headers:
        headers['Content-length'] = str(len(raw))
    body_parsers = {
            "application/json": parsers.jsondata,
            "application/x-www-form-urlencoded": parsers.formdata,
            "multipart/form-data": parsers.formdata
    }
    headers['Host'] = 'Blah'
    return parsers.parse_body(raw, Headers(headers), body_parsers)


def test_body_is_unparsed_for_empty_content_type():
    raw = "cheese=yes"
    raises(UnknownBodyType, make_body, raw, headers={})

def test_body_barely_works():
    body = make_body("cheese=yes")
    actual = body['cheese']
    assert actual == "yes"


UPLOAD = """\
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
Content-Disposition: form-data; name="files"; filename="file1.txt"
Content-Type: text/plain

... contents of file1.txt ...
--AaB03x--
"""

def test_body_barely_works_for_form_data():
    body = make_body(UPLOAD, content_type=FORMDATA)
    actual = body['files'].filename
    assert actual == "file1.txt"

def test_simple_values_are_simple():
    body = make_body(UPLOAD, content_type=FORMDATA)
    actual = body['submit-name']
    assert actual == "Larry"

def test_multiple_values_are_multiple():
    body = make_body("cheese=yes&cheese=burger")
    actual = body['cheese']
    assert actual == "yes"

def test_params_doesnt_break_www_form():
    body = make_body("statement=foo"
                    , content_type="application/x-www-form-urlencoded; charset=UTF-8; cheese=yummy"
                     )
    actual = body['statement']
    assert actual == "foo"

def test_malformed_body_jsondata():
    with raises(MalformedBody):
        make_body("foo", content_type="application/json")

def test_malformed_body_formdata():
    with raises(MalformedBody):
        make_body("", content_type="multipart/form-data; boundary=\0")
