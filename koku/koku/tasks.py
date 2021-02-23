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
"""Prometheus metrics."""
import logging

from django.conf import settings
from prometheus_client import CollectorRegistry
from prometheus_client import push_to_gateway

from .celery import app
from .metrics import DatabaseStatus

LOG = logging.getLogger(__name__)
REGISTRY = CollectorRegistry()


@app.task(name="koku.tasks.collect_metrics", bind=True)
def collect_metrics(self):
    """Collect DB metrics with scheduled celery task."""
    db_status = DatabaseStatus()
    db_status.connection_check()
    db_status.collect()
    LOG.debug("Pushing stats to gateway: %s", settings.PROMETHEUS_PUSHGATEWAY)
    try:
        push_to_gateway(settings.PROMETHEUS_PUSHGATEWAY, job="koku.metrics.collect_metrics", registry=REGISTRY)
    except OSError as exc:
        LOG.error("Problem reaching pushgateway: %s", exc)
        self.update_state(state="FAILURE", meta={"result": str(exc), "traceback": str(exc.__traceback__)})
