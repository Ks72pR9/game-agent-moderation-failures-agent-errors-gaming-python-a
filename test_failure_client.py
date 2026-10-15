from failure_client import FailureClient, InfraiError


class Response:
    status_code = 400
    headers: dict[str, str] = {}

    def json(self) -> dict[str, object]:
        return {"ok": False, "data": None, "error": {"code": "TEST_REJECTION"}, "metadata": {}}


class Session:
    def request(self, **kwargs: object) -> Response:
        self.kwargs = kwargs
        return Response()


def test_client_decodes_rejection_before_status_handling() -> None:
    session = Session()
    client = FailureClient(api_key="test-key", session=session)  # type: ignore[arg-type]

    try:
        client.capture({"message": "test"}, "event-test")
    except InfraiError as exc:
        assert exc.status_code == 400
        assert exc.error == {"code": "TEST_REJECTION"}
    else:
        raise AssertionError("expected decoded rejection")

    assert session.kwargs["method"] == "POST"
    assert session.kwargs["json"] == {"exception": {"message": "test"}}
