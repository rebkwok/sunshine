from ..views.misc import csrf_failure


def test_csrf_failure_view(rf):
    request = rf.post("/")
    resp = csrf_failure(request)
    assert "Sorry, we encountered a minor blip" in resp.content.decode("utf-8")
