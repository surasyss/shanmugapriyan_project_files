import datetime
from typing import Optional

from django.db.models import Sum

from apps.jobconfig.models import Frequency, Job, JobSchedule, JobStat

EMAIL_TEMPLATES = {
    "nif-cs-in-24-hours": {
        "subject": "Action Required: No invoices found in 24 hours for {connector_name}.",
        "content": "Hi {first_name},<br><br>"
        "The connection with {connector_name} for the username: {username}. "
        "Invoices not found in the vendor portal in last 24 hours.<br><br>",
    },
    "nif-cs-in-48-hours": {
        "subject": "Action Required: No invoices found in 48 hours for {connector_name}.",
        "content": "Hi {first_name},<br><br>"
        "The connection with {connector_name} for the username: {username}. "
        "Invoices not found in the vendor portal in last 48 hours.<br><br>",
    },
    "icl-weekly": {
        "subject": "Weekly - Downloaded Invoice count is lower than expected",
        "content": "Hi {first_name},<br><br>"
        "The connection with {connector_name} for the username: {username}. "
        "No of invoices downloaded are less than the expected.<br><br>",
    },
    "icl-fortnightly": {
        "subject": "Fortnightly - Downloaded Invoice count is lower than expected",
        "content": "Hi {first_name},<br><br>"
        "The connection with {connector_name} for the username: {username}. "
        "No of invoices downloaded are less than the expected.<br><br>",
    },
    "icl-monthly": {
        "subject": "Monthly - Downloaded Invoice count is lower than expected",
        "content": "Hi {first_name},<br><br>"
        "The connection with {connector_name} for the username: {username}. "
        "No of invoices downloaded are less than the expected.<br><br>",
    },
}


def get_total_df_count(
    job: Job, start_date: datetime.date, end_ts: datetime.date
) -> int:
    """Get total df count within date range"""
    # throw exception if start_date and end_date are not `date` type
    if not isinstance(start_date, datetime.date) or not isinstance(
        end_ts, datetime.date
    ):
        raise Exception(
            f"[SLAGTDC10] Invalid date type, start_date : {start_date}, end_date : {end_ts}"
        )
    stat = JobStat.objects.filter(
        date__gte=start_date,
        date__lte=end_ts,
        job_id=job.id,
    ).aggregate(total_document_count=Sum("df_count"))

    return stat.get("total_document_count")


def get_total_df_count_for_current_period(
    job: Job, frequency: Frequency, now: datetime.datetime
) -> int:
    """Get total df count within current period as per the frequency"""
    # for given value of `now`, derive start and end dates based on the frequency.
    # for week it will be the current Sunday to now
    # for month it will be the 1st of current month to now
    # etc
    if not isinstance(now, datetime.datetime):
        raise Exception(f"[SLAGTDC10] Invalid datetime type, now : {now}")
    stat = None
    if frequency == Frequency.WEEKLY:
        sunday = (
            now - datetime.timedelta(days=now.weekday()) - datetime.timedelta(days=1)
        )
        stat = get_total_df_count(job, sunday, now)
    elif frequency == Frequency.MONTHLY:
        today = now.date()
        first_of_month = today.replace(day=1)
        stat = get_total_df_count(job, first_of_month, now)
    return stat


def get_total_df_count_for_previous_period(
    job: Job, frequency: Frequency, now: datetime.datetime
) -> int:
    """Get total df count within previous period as per the frequency"""
    # for given value of `now`, derive start and end dates based on the frequency.
    # for week it will be the previous Sunday to Saturday
    # for month it will be the previous calendar month
    # etc
    if not isinstance(now, datetime.datetime):
        raise Exception(f"[SLAGTDC10] Invalid datetime type, now : {now}")
    stat = None
    if frequency == Frequency.WEEKLY:
        last_week = now.date().toordinal() - 7
        sunday = last_week - (last_week % 7)
        stat = get_total_df_count(
            job,
            datetime.date.fromordinal(sunday),
            datetime.date.fromordinal(sunday) + datetime.timedelta(days=6),
        )
    elif frequency == Frequency.MONTHLY:
        today = now.date()
        last_of_month = today.replace(day=1) - datetime.timedelta(days=1)
        first_of_month = last_of_month.replace(day=1)
        stat = get_total_df_count(job, first_of_month, last_of_month)
    return stat


def is_sla_breached(job_schedule: JobSchedule, now: datetime.datetime) -> bool:
    # for week you'll need to call `get_total_df_count_for_current_period`
    # for month you'll need to call `get_total_df_count_for_previous_period`
    ret_value = False
    if job_schedule.frequency == Frequency.MONTHLY.ident:
        stat = get_total_df_count_for_previous_period(
            job_schedule.job, Frequency.MONTHLY, now
        )
        ret_value = True if not stat else False
    elif job_schedule.frequency == Frequency.WEEKLY.ident:
        stat = get_total_df_count_for_current_period(
            job_schedule.job, Frequency.WEEKLY, now
        )
        ret_value = True if not stat else False
    return ret_value


def is_valid_time_to_send_sla_breach_email(
    job_schedule, now: datetime.datetime
) -> bool:
    """Following method validates the current date as per the job-schedule frequency
    hardcoding 'saturday' and '5th of every month' values here"""
    ret_value = False
    if job_schedule.frequency == Frequency.MONTHLY.ident:
        if now.day == 5:
            ret_value = True
    elif job_schedule.frequency == Frequency.WEEKLY.ident:
        if now.weekday() == 5:
            ret_value = True
    return ret_value


def get_sla_breach_email_content(
    job_schedule: JobSchedule, now: datetime.datetime
) -> Optional[dict]:
    """ """
    # TODO: fill this out and write tests. Call this from your command file.

    if not is_valid_time_to_send_sla_breach_email(job_schedule, now):
        return None

    if not is_sla_breached(job_schedule, now):
        return None

    # move get_email_content logic here
    state = ""
    param = job_schedule.frequency
    if param == Frequency.WEEKLY:
        state = "icl-weekly"
    elif param == Frequency.FORTNIGHTLY:
        state = "icl-fortnightly"
    elif param == Frequency.MONTHLY:
        state = "icl-monthly"
    elif param == Frequency.DAILY:
        state = "nif-cs-in-24-hours"
    # TODO need to add condition for nif-cs-in-48-hours
    if not state:
        return {}
    job = job_schedule.job
    return {
        # "to_email": job.get_created_user_email(),
        "to_email": "gaurav@plateiq.com",
        "subject": EMAIL_TEMPLATES[state]["subject"].format(
            connector_name=job.connector.name
        ),
        "content": EMAIL_TEMPLATES[state]["content"].format(
            first_name=job.created_user.first_name,
            username=job.username,
            connector_name=job.connector.name,
        ),
    }
