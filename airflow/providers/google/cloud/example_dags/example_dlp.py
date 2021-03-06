#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Example Airflow DAG that execute the following tasks using
Cloud DLP service in the Google Cloud Platform:
1) Creating a content inspect template;
2) Using the created template to inspect content;
3) Deleting the template from GCP .
"""

import os

from google.cloud.dlp_v2.types import ContentItem, InspectConfig, InspectTemplate

from airflow import models
from airflow.providers.google.cloud.operators.dlp import (
    CloudDLPCreateInspectTemplateOperator,
    CloudDLPCreateJobTriggerOperator,
    CloudDLPCreateStoredInfoTypeOperator,
    CloudDLPDeleteInspectTemplateOperator,
    CloudDLPDeleteJobTriggerOperator,
    CloudDLPDeleteStoredInfoTypeOperator,
    CloudDLPInspectContentOperator,
    CloudDLPUpdateJobTriggerOperator,
    CloudDLPUpdateStoredInfoTypeOperator,
)
from airflow.utils.dates import days_ago

GCP_PROJECT = os.environ.get("GCP_PROJECT_ID", "example-project")
TEMPLATE_ID = "dlp-inspect-838746"
ITEM = ContentItem(
    table={
        "headers": [{"name": "column1"}],
        "rows": [{"values": [{"string_value": "My phone number is (206) 555-0123"}]}],
    }
)
INSPECT_CONFIG = InspectConfig(info_types=[{"name": "PHONE_NUMBER"}, {"name": "US_TOLLFREE_PHONE_NUMBER"}])
INSPECT_TEMPLATE = InspectTemplate(inspect_config=INSPECT_CONFIG)


with models.DAG(
    "example_gcp_dlp",
    schedule_interval=None,  # Override to match your needs
    start_date=days_ago(1),
    tags=['example'],
) as dag:
    # [START howto_operator_dlp_create_inspect_template]
    create_template = CloudDLPCreateInspectTemplateOperator(
        project_id=GCP_PROJECT,
        inspect_template=INSPECT_TEMPLATE,
        template_id=TEMPLATE_ID,
        task_id="create_template",
        do_xcom_push=True,
        dag=dag,
    )
    # [END howto_operator_dlp_create_inspect_template]

    # [START howto_operator_dlp_use_inspect_template]
    inspect_content = CloudDLPInspectContentOperator(
        task_id="inpsect_content",
        project_id=GCP_PROJECT,
        item=ITEM,
        inspect_template_name="{{ task_instance.xcom_pull('create_template', key='return_value')['name'] }}",
        dag=dag,
    )
    # [END howto_operator_dlp_use_inspect_template]

    # [START howto_operator_dlp_delete_inspect_template]
    delete_template = CloudDLPDeleteInspectTemplateOperator(
        task_id="delete_template", template_id=TEMPLATE_ID, project_id=GCP_PROJECT, dag=dag,
    )
    # [END howto_operator_dlp_delete_inspect_template]

    create_template >> inspect_content >> delete_template


CUSTOM_INFO_TYPES = [{"info_type": {"name": "C_MRN"}, "regex": {"pattern": "[1-9]{3}-[1-9]{1}-[1-9]{5}"},}]
CUSTOM_INFO_TYPE_ID = "custom_info_type"
UPDATE_CUSTOM_INFO_TYPE = [
    {"info_type": {"name": "C_MRN"}, "regex": {"pattern": "[a-z]{3}-[a-z]{1}-[a-z]{5}"},}
]

with models.DAG(
    "example_gcp_dlp_info_types",
    schedule_interval=None,
    start_date=days_ago(1),
    tags=["example", "dlp", "info-types"],
) as dag:
    # [START howto_operator_dlp_create_info_type]
    create_info_type = CloudDLPCreateStoredInfoTypeOperator(
        project_id=GCP_PROJECT,
        config=CUSTOM_INFO_TYPES,
        stored_info_type_id=CUSTOM_INFO_TYPE_ID,
        dag=dag,
        task_id="create_info_type",
    )
    # [END howto_operator_dlp_create_info_type]
    # [START howto_operator_dlp_update_info_type]
    update_info_type = CloudDLPUpdateStoredInfoTypeOperator(
        project_id=GCP_PROJECT,
        stored_info_type_id=CUSTOM_INFO_TYPE_ID,
        config=UPDATE_CUSTOM_INFO_TYPE,
        dag=dag,
        task_id="update_info_type",
    )
    # [END howto_operator_dlp_update_info_type]
    # [START howto_operator_dlp_delete_info_type]
    delete_info_type = CloudDLPDeleteStoredInfoTypeOperator(
        project_id=GCP_PROJECT, stored_info_type_id=CUSTOM_INFO_TYPE_ID, dag=dag, task_id="delete_info_type",
    )
    # [END howto_operator_dlp_delete_info_type]
    create_info_type >> update_info_type >> delete_info_type

SCHEDULE = {"recurrence_period_duration": {"seconds": 60 * 60 * 24}}
JOB = {
    "inspect_config": INSPECT_CONFIG,
}

JOB_TRIGGER = {
    "inspect_job": JOB,
    "triggers": [{"schedule": SCHEDULE}],
    "status": "HEALTHY",
}

TRIGGER_ID = "example_trigger"

with models.DAG(
    "example_gcp_dlp_job", schedule_interval=None, start_date=days_ago(1), tags=["example", "dlp_job"],
) as dag:  # [START howto_operator_dlp_create_job_trigger]
    create_trigger = CloudDLPCreateJobTriggerOperator(
        project_id=GCP_PROJECT,
        job_trigger=JOB_TRIGGER,
        trigger_id=TRIGGER_ID,
        dag=dag,
        task_id="create_trigger",
    )
    # [END howto_operator_dlp_create_job_trigger]
    UPDATED_SCHEDULE = {"recurrence_period_duration": {"seconds": 2 * 60 * 60 * 24}}

    JOB_TRIGGER["triggers"] = [{"schedule": UPDATED_SCHEDULE}]

    # [START howto_operator_dlp_update_job_trigger]
    update_trigger = CloudDLPUpdateJobTriggerOperator(
        project_id=GCP_PROJECT,
        job_trigger_id=TRIGGER_ID,
        job_trigger=JOB_TRIGGER,
        dag=dag,
        task_id="update_info_type",
    )
    # [END howto_operator_dlp_update_job_trigger]
    # [START howto_operator_dlp_delete_job_trigger]
    delete_trigger = CloudDLPDeleteJobTriggerOperator(
        project_id=GCP_PROJECT, job_trigger_id=TRIGGER_ID, dag=dag, task_id="delete_info_type",
    )
    # [END howto_operator_dlp_delete_job_trigger]
    create_trigger >> update_trigger >> delete_trigger
