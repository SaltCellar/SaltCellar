#
# Copyright 2021 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Summary Updater for GCP Parquet files."""
import calendar
import logging

import ciso8601
from tenant_schemas.utils import schema_context

from masu.database.cost_model_db_accessor import CostModelDBAccessor
from masu.database.gcp_report_db_accessor import GCPReportDBAccessor
from masu.external.date_accessor import DateAccessor
from masu.util.common import determine_if_full_summary_update_needed

LOG = logging.getLogger(__name__)


class GCPReportParquetSummaryUpdater:
    """Class to update GCP report parquet summary data."""

    def __init__(self, schema, provider, manifest):
        """Establish parquet summary processor."""
        self._schema = schema
        self._provider = provider
        self._manifest = manifest
        self._date_accessor = DateAccessor()

    def _get_sql_inputs(self, start_date, end_date):
        """Get the required inputs for running summary SQL."""
        with GCPReportDBAccessor(self._schema) as accessor:
            # This is the normal processing route
            if self._manifest:
                # Override the bill date to correspond with the manifest
                bill_date = self._manifest.billing_period_start_datetime.date()
                bills = accessor.get_cost_entry_bills_query_by_provider(self._provider.uuid)
                bills = bills.filter(billing_period_start=bill_date).all()
                first_bill = bills.filter(billing_period_start=bill_date).first()
                do_month_update = False
                with schema_context(self._schema):
                    if first_bill:
                        do_month_update = determine_if_full_summary_update_needed(first_bill)
                if do_month_update:
                    last_day_of_month = calendar.monthrange(bill_date.year, bill_date.month)[1]
                    start_date = bill_date
                    end_date = bill_date.replace(day=last_day_of_month)
                    LOG.info("Overriding start and end date to process full month.")

        if isinstance(start_date, str):
            start_date = ciso8601.parse_datetime(start_date).date()
        if isinstance(end_date, str):
            end_date = ciso8601.parse_datetime(end_date).date()

        return start_date, end_date

    def update_daily_tables(self, start_date, end_date):
        """Populate the daily tables for reporting.

        Args:
            start_date (str) The date to start populating the table.
            end_date   (str) The date to end on.

        Returns
            (str, str): A start date and end date.

        """
        start_date, end_date = self._get_sql_inputs(start_date, end_date)
        LOG.info("update_daily_tables for: %s-%s", str(start_date), str(end_date))

        return start_date, end_date

    def update_summary_tables(self, start_date, end_date):
        """Populate the summary tables for reporting.

        Args:
            start_date (str) The date to start populating the table.
            end_date   (str) The date to end on.

        Returns
            (str, str) A start date and end date.

        """
        start_date, end_date = self._get_sql_inputs(start_date, end_date)

        with CostModelDBAccessor(self._schema, self._provider.uuid) as cost_model_accessor:
            markup = cost_model_accessor.markup
            markup_value = float(markup.get("value", 0)) / 100

        with GCPReportDBAccessor(self._schema) as accessor:
            # Need these bills on the session to update dates after processing
            with schema_context(self._schema):
                bills = accessor.bills_for_provider_uuid(self._provider.uuid, start_date)
                bill_ids = [str(bill.id) for bill in bills]
                current_bill_id = bills.first().id if bills else None

            if current_bill_id is None:
                msg = f"No bill was found for {start_date}. Skipping summarization"
                LOG.info(msg)
                return start_date, end_date

            # for start, end in date_range_pair(start_date, end_date):
            LOG.info(
                "Updating GCP report summary tables from parquet: \n\tSchema: %s"
                "\n\tProvider: %s \n\tDates: %s - %s",
                self._schema,
                self._provider.uuid,
                start_date,
                end_date,
            )
            accessor.delete_line_item_daily_summary_entries_for_date_range(self._provider.uuid, start_date, end_date)
            accessor.populate_line_item_daily_summary_table_presto(
                start_date, end_date, self._provider.uuid, current_bill_id, markup_value
            )
            accessor.populate_enabled_tag_keys(start_date, end_date, bill_ids)
            accessor.populate_tags_summary_table(bill_ids)
            accessor.update_line_item_daily_summary_with_enabled_tags(start_date, end_date, bill_ids)
            for bill in bills:
                if bill.summary_data_creation_datetime is None:
                    bill.summary_data_creation_datetime = self._date_accessor.today_with_timezone("UTC")
                bill.summary_data_updated_datetime = self._date_accessor.today_with_timezone("UTC")
                bill.save()

        return start_date, end_date