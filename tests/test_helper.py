import pytest
from app.helper import sanitize_input


class TestSanitizeInput:
    def test_none_input(self):
        assert sanitize_input(None) is None

    def test_non_string_input(self):
        assert sanitize_input(123) == 123
        assert sanitize_input(3.14) == 3.14
        assert sanitize_input([1, 2]) == [1, 2]

    def test_clean_string_unchanged(self):
        result = sanitize_input('hello world')
        assert result == 'hello world'

    def test_removes_script_tags(self):
        result = sanitize_input('<script>alert("xss")</script>')
        assert 'script' not in result
        assert result == ''

    def test_removes_script_with_attrs(self):
        result = sanitize_input('<script type="text/javascript">evil()</script>')
        assert result == ''

    def test_removes_iframe(self):
        result = sanitize_input('<iframe src="http://evil.com"></iframe>')
        assert 'iframe' not in result
        assert result == ''

    def test_removes_embed(self):
        result = sanitize_input('<embed src="http://evil.com">')
        assert result == ''

    def test_removes_object(self):
        result = sanitize_input('<object data="http://evil.com"></object>')
        assert result == ''

    def test_removes_form(self):
        result = sanitize_input('<form action="http://evil.com"></form>')
        assert result == ''

    def test_removes_input(self):
        result = sanitize_input('<input type="hidden" value="evil">')
        assert result == ''

    def test_removes_button(self):
        result = sanitize_input('<button onclick="steal()">click</button>')
        assert result == 'click'

    def test_removes_style(self):
        result = sanitize_input('<style>body{background:red}</style>')
        assert 'style' not in result.lower()

    def test_removes_link(self):
        result = sanitize_input('<link rel="stylesheet" href="evil.css">')
        assert result == ''

    def test_removes_meta(self):
        result = sanitize_input('<meta http-equiv="refresh" content="0;url=http://evil.com">')
        assert result == ''

    def test_removes_onclick_handler(self):
        result = sanitize_input('<div onclick="alert(1)">text</div>')
        assert 'onclick' not in result
        assert 'text' in result

    def test_removes_onerror_handler(self):
        result = sanitize_input('<img src=x onerror="alert(1)">')
        assert 'onerror' not in result

    def test_removes_javascript_href(self):
        result = sanitize_input('<a href="javascript:alert(1)">link</a>')
        assert 'javascript' not in result.lower()

    def test_removes_javascript_src(self):
        result = sanitize_input('<img src="javascript:alert(1)">')
        assert 'javascript' not in result.lower()

    def test_preserves_safe_html(self):
        result = sanitize_input('<p>Hello <b>world</b></p>')
        assert result == '<p>Hello <b>world</b></p>'

    def test_combined_attack_vector(self):
        result = sanitize_input('<div><script>evil()</script><p onclick="x()">text</p></div>')
        assert 'script' not in result
        assert 'onclick' not in result
        assert '<p>' in result
        assert 'text' in result
