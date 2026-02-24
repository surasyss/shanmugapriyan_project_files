from unittest import mock

import pytest
from django.conf import settings
from django.core.management import call_command


# @mock.patch("spices.celery_utils.get_queue_length")
# def test__celery_queue_notify__success(mock_get_queue_length):
#     queue_length = {
#         "integrator-tasks": 10,
#         "integrator-short-tasks": 20,
#         "integrator-tasks-on-demand": 30,
#     }

#     mock_get_queue_length.return_value = queue_length

#     with mock.patch.object(settings.SLACK_CLIENT, "message") as mock_slack:
#         call_command("celery_queue_notify", notify="true", notify_threshold=19)

#         assert mock_slack.call_count == 2


@mock.patch("spices.celery_utils.get_queue_length")
def test__celery_queue_notify__with_notify_and_without_notify_threshold(
    mock_get_queue_length,
):
    queue_length = {
        "integrator-tasks": 10,
        "integrator-short-tasks": 20,
        "integrator-tasks-on-demand": 30,
    }

    mock_get_queue_length.return_value = queue_length

    with pytest.raises(Exception) as ex:
        call_command("celery_queue_notify", notify="true")

    assert ex.value.args[0] == "To enable notify please pass 'notify-threshold' as well"


@pytest.mark.parametrize("notify_threshold", ["abc"])
@mock.patch("spices.celery_utils.get_queue_length")
def test__celery_queue_notify___notify_threshold_not_int(
    mock_get_queue_length, notify_threshold
):
    queue_length = {
        "integrator-tasks": 10,
        "integrator-short-tasks": 20,
        "integrator-tasks-on-demand": 30,
    }

    mock_get_queue_length.return_value = queue_length

    with pytest.raises(Exception) as ex:
        call_command(
            "celery_queue_notify", notify="true", notify_threshold=notify_threshold
        )

    assert ex.value.args[0] == "notify-threshold must be a number"
