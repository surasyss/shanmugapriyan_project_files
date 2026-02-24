# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from spices.django3.coreobjects.base import (
    CoreObjectClientException,
    CoreObjectServerException,
)
from spices.django3.coreobjects.models import Company

from apps.jobconfig.models import Job
from apps.utils.piq_core import PIQCoreClient
from integrator.conf import PIQ_API_BASE_URL, PIQ_API_TOKEN


def set_company_ids(apps, schema_editor):
    if settings.LOCAL_ENV:
        return

    jobs_with_candidate_restaurant_ids = Job.objects.exclude(
        candidate_restaurant_ids__isnull=True
    )
    piq_client = PIQCoreClient(PIQ_API_BASE_URL, PIQ_API_TOKEN)

    for job in jobs_with_candidate_restaurant_ids:
        for restaurant_id in job.candidate_restaurant_ids:
            if restaurant_id == -1:
                continue

            try:
                json_response = piq_client.get_restaurant_by_id(restaurant_id)
                company = json_response["company"]
                if company:
                    company_shared_obj = Company.retrieve(
                        None, company["id"], cache_locally=True
                    )
                    job.companies.add(company_shared_obj)
            except CoreObjectClientException as e:
                print(f"Error occurred while fetching Company: {company['id']}")
            except CoreObjectServerException as e:
                print(f"Error occurred while fetching Company: {company['id']}")


class Migration(migrations.Migration):
    dependencies = [
        ("jobconfig", "0006_job_company"),
    ]

    operations = [migrations.RunPython(set_company_ids, atomic=True)]
