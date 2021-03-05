#
# Copyright 2018 Red Hat, Inc.
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
"""OCP Query Handling for Reports."""
import logging

from api.models import Provider
from api.report.all.openshift.provider_map import OCPAllProviderMap
from api.report.aws.openshift.query_handler import OCPInfrastructureReportQueryHandlerBase
from api.report.queries import is_grouped_by_project

LOG = logging.getLogger(__name__)


class OCPAllReportQueryHandler(OCPInfrastructureReportQueryHandlerBase):
    """Handles report queries and responses for OCP on All Infrastructure."""

    provider = Provider.OCP_ALL
    network_services = {
        "AmazonVPC",
        "AmazonCloudFront",
        "AmazonRoute53",
        "AmazonAPIGateway",
        "Virtual Network",
        "VPN",
        "DNS",
        "Traffic Manager",
        "ExpressRoute",
        "Load Balancer",
        "Application Gateway",
    }
    database_services = {
        "AmazonRDS",
        "AmazonDynamoDB",
        "AmazonElastiCache",
        "AmazonNeptune",
        "AmazonRedshift",
        "AmazonDocumentDB",
        "Database",
        "Cosmos DB",
        "Cache for Redis",
    }

    def __init__(self, parameters):
        """Establish OCP report query handler.
        Args:
            parameters    (QueryParameters): parameter object for query
        """
        self._mapper = OCPAllProviderMap(provider=self.provider, report_type=parameters.report_type)
        # Update which field is used to calculate cost by group by param.
        if is_grouped_by_project(parameters):
            self._report_type = parameters.report_type + "_by_project"
            self._mapper = OCPAllProviderMap(provider=self.provider, report_type=self._report_type)

        self.group_by_options = self._mapper.provider_map.get("group_by_options")
        self._limit = parameters.get_filter("limit")

        # super() needs to be called after _mapper and _limit is set
        super().__init__(parameters)
