from unittest.mock import Mock, patch

import pytest
import requests

from malmo_council_attendance.io import get_api_json, get_page_html


@pytest.mark.parametrize(
    "expected",
    [
        {"Items": [{"Id": 1, "Name": "Testperson"}]},
        [{"RepresentativeId": 1, "Role": "Ledamot"}],
    ],
)
def test_get_api_json_returns_json_and_logs_success(expected):
    url = "https://example.test/api"
    response = Mock()
    response.status_code = 200
    response.json.return_value = expected

    with (
        patch(
            "malmo_council_attendance.io.requests.get",
            return_value=response,
        ) as mock_get,
        patch("malmo_council_attendance.io.logger.info") as mock_info,
    ):
        result = get_api_json(url)

    assert result == expected
    mock_get.assert_called_once_with(url, timeout=30)
    response.raise_for_status.assert_called_once_with()
    mock_info.assert_called_once_with(
        "API-anrop lyckades: %s (HTTP %s)",
        url,
        200,
    )


def test_get_api_json_does_not_log_http_error():
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("Serverfel")

    with (
        patch(
            "malmo_council_attendance.io.requests.get",
            return_value=response,
        ),
        patch("malmo_council_attendance.io.logger.info") as mock_info,
        patch("malmo_council_attendance.io.logger.exception") as mock_exception,
        pytest.raises(requests.HTTPError),
    ):
        get_api_json("https://example.test/api")

    mock_info.assert_not_called()
    mock_exception.assert_called_once_with(
        "API-anrop misslyckades: %s",
        "https://example.test/api",
    )


def test_get_page_html_returns_response_and_logs_success():
    url = "https://example.test/meetings"
    response = Mock(status_code=200, text="<h1>Meeting</h1>")

    with (
        patch(
            "malmo_council_attendance.io.requests.get",
            return_value=response,
        ) as mock_get,
        patch("malmo_council_attendance.io.logger.info") as mock_info,
    ):
        result = get_page_html(url)

    assert result.h1.get_text() == "Meeting"
    mock_get.assert_called_once_with(url, timeout=30)
    response.raise_for_status.assert_called_once_with()
    mock_info.assert_called_once_with(
        "Webbsidan hämtades: %s (HTTP %s)",
        url,
        200,
    )


def test_get_page_html_logs_http_error_and_reraises():
    url = "https://example.test/meetings"
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("Serverfel")

    with (
        patch(
            "malmo_council_attendance.io.requests.get",
            return_value=response,
        ),
        patch("malmo_council_attendance.io.logger.exception") as mock_exception,
        pytest.raises(requests.HTTPError),
    ):
        get_page_html(url)

    mock_exception.assert_called_once_with(
        "Hämtning av webbsidan misslyckades: %s",
        url,
    )