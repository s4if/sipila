from app.helper import sanitize


class TestSanitizeInput:
    def test_none_input(self):
        assert sanitize(None) is None

    def test_non_string_input(self):
        assert sanitize(123) == 123
        assert sanitize(3.14) == 3.14
        assert sanitize([1, 2]) == [1, 2]

    def test_clean_string_unchanged(self):
        result = sanitize("hello world")
        assert result == "hello world"

    def test_removes_script_tags(self):
        result = sanitize('<script>alert("xss")</script>')
        assert "script" not in result
        assert result == ""

    def test_removes_script_with_attrs(self):
        result = sanitize('<script type="text/javascript">evil()</script>')
        assert result == ""

    def test_removes_iframe(self):
        result = sanitize('<iframe src="http://evil.com"></iframe>')
        assert "iframe" not in result
        assert result == ""

    def test_removes_embed(self):
        result = sanitize('<embed src="http://evil.com">')
        assert result == ""

    def test_removes_object(self):
        result = sanitize('<object data="http://evil.com"></object>')
        assert result == ""

    def test_removes_form(self):
        result = sanitize('<form action="http://evil.com"></form>')
        assert result == ""

    def test_removes_input(self):
        result = sanitize('<input type="hidden" value="evil">')
        assert result == ""

    def test_removes_button(self):
        result = sanitize('<button onclick="steal()">click</button>')
        assert result == "click"

    def test_removes_style(self):
        result = sanitize("<style>body{background:red}</style>")
        assert "style" not in result.lower()

    def test_removes_link(self):
        result = sanitize('<link rel="stylesheet" href="evil.css">')
        assert result == ""

    def test_removes_meta(self):
        result = sanitize(
            '<meta http-equiv="refresh" content="0;url=http://evil.com">'
        )
        assert result == ""

    def test_removes_onclick_handler(self):
        result = sanitize('<div onclick="alert(1)">text</div>')
        assert "onclick" not in result
        assert "text" in result

    def test_removes_onerror_handler(self):
        result = sanitize('<img src=x onerror="alert(1)">')
        assert "onerror" not in result

    def test_removes_javascript_href(self):
        result = sanitize('<a href="javascript:alert(1)">link</a>')
        assert "javascript" not in result.lower()

    def test_removes_javascript_src(self):
        result = sanitize('<img src="javascript:alert(1)">')
        assert "javascript" not in result.lower()

    def test_preserves_safe_html(self):
        result = sanitize("<p>Hello <b>world</b></p>")
        assert result == "<p>Hello <b>world</b></p>"

    def test_combined_attack_vector(self):
        result = sanitize(
            '<div><script>evil()</script><p onclick="x()">text</p></div>'
        )
        assert "script" not in result
        assert "onclick" not in result
        assert "<p>" in result
        assert "text" in result


class TestSuperadminRequired:
    def test_no_session_redirects_to_login(self, client):
        response = client.get("/admin/guru")
        assert response.status_code == 302
        assert "login" in response.location

    def test_regular_admin_redirects_to_beranda(self, client):
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["is_admin"] = True
            sess["is_superadmin"] = False
            sess["admin_name"] = "regular"
        response = client.get("/admin/guru")
        assert response.status_code == 302
        assert "/admin/" in response.location
        assert "login" not in response.location

    def test_superadmin_allowed(self, logged_in_client):
        response = logged_in_client.get("/admin/guru")
        assert response.status_code == 200

    def test_is_admin_false_redirects_to_login(self, client):
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["is_admin"] = False
            sess["is_superadmin"] = True
            sess["admin_name"] = "fake"
        response = client.get("/admin/guru")
        assert response.status_code == 302
        assert "login" in response.location

    def test_missing_admin_name_redirects_to_login(self, client):
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["is_admin"] = True
            sess["is_superadmin"] = True
        response = client.get("/admin/guru")
        assert response.status_code == 302
        assert "login" in response.location

    def test_missing_is_superadmin_key_redirects_to_beranda(self, client):
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["is_admin"] = True
            sess["admin_name"] = "admin"
        response = client.get("/admin/guru")
        assert response.status_code == 302
        assert "/admin/" in response.location
        assert "login" not in response.location
