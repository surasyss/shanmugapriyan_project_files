import calendar
import datetime
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from apps.jobconfig.models import JobStat, Period, JobAlertRule


def __get_previous_month_range(date):
    previous_month_date = date.replace(month=date.month - 1)
    first_day = previous_month_date.replace(day=1)
    last_day = previous_month_date.replace(
        day=calendar.monthrange(previous_month_date.year, previous_month_date.month)[1]
    )
    return first_day, last_day


def _get_date_range(period, date):
    if not date:
        date = timezone.now().date()

    if isinstance(date, datetime.datetime):
        date = date.date()

    if not isinstance(date, datetime.date):
        raise Exception("Type of 'date' must be datetime.date or datetime.datetime")

    current_date = date
    if period == Period.DAY.ident:
        previous_date = current_date - timedelta(days=1)
        return previous_date, previous_date

    if period == Period.WEEK.ident:
        start_delta = datetime.timedelta(days=current_date.weekday(), weeks=1)
        start = current_date - start_delta
        end = start + timedelta(days=6)
        return start, end

    if period == Period.MONTH.ident:
        return __get_previous_month_range(date)

        start = current_date.replace(day=1)
        end = current_date.replace(
            day=calendar.monthrange(current_date.year, current_date.month)[1]
        )
        return start, end


def _should_alert(expected_document_count, actual_document_count):
    if actual_document_count is None and expected_document_count > 0:
        return True

    if actual_document_count < expected_document_count:
        return True


class Command(BaseCommand):
    """
    For weekly alerts, run the job on Monday, this will give alert for the previous week.
        Example: Running the job on 14 June, 2021, will give result of June 7, 2021 to June 13, 2021
    For monthly alerts, run the job on 1st of every month, this will give alert for the previous month
        Example: Running the job on 01 June, 2021, will give result of May 01, 2021 to May 31, 2021
    """

    help = "Alert about job output"

    def add_arguments(self, parser):
        parser.add_argument(
            "--period",
            dest="period",
            help="Alert Period - Options (daily/monthly/weekly)",
        )

    def handle(self, *args, **options):
        period = options["period"]

        if not period:
            raise Exception(
                "Period is a required argument. Possible values are 'Day', 'Week', 'Month'"
            )

        period = Period.from_name(period.upper())
        if not period:
            raise Exception(
                "Invalid period value. Possible values are 'Day', 'Week', 'Month'"
            )

        current_date = timezone.now()
        alert_rules = (
            JobAlertRule.objects.select_related("job")
            .filter(
                period=period.ident,
                enabled=True,
                job__enabled=True,
                job__connector__enabled=True,
            )
            .exclude(job__connector__adapter_code="backlog")
        )

        for rule in alert_rules:
            period = rule.period
            expected_document_count = rule.expected_document_count
            start, end = _get_date_range(period, current_date)
            stat = JobStat.objects.filter(
                date__gte=start, date__lte=end, job_id=rule.job_id
            ).aggregate(total_document_count=Sum("df_count"))

            if _should_alert(expected_document_count, stat.get("total_document_count")):
                settings.SLACK_CLIENT.message(
                    settings.SLACK_CHANNEL,
                    f":exclamation: Alert - For job {rule.job_id} in {period}, expected document count is "
                    f"{expected_document_count} while the actual document downloaded is {stat}",
                )
