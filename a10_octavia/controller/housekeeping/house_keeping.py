#    Copyright 2019, A10 Networks
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from concurrent import futures
import datetime
from datetime import datetime as dt_funcs

from oslo_config import cfg
from oslo_log import log as logging

from octavia.db import api as db_api

from a10_octavia.controller.worker import controller_worker as cw
from a10_octavia.db import repositories as a10repo

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class SpareAmphora(object):
    def __init__(self):
        self.vthunder_repo = a10repo.VThunderRepository()
        self.cw = cw.A10ControllerWorker()

    def spare_check(self):
        """Checks the DB for the Spare amphora count.

        If it's less than the requirement, starts new amphora.
        """
        session = db_api.get_session()
        conf_spare_cnt = CONF.a10_house_keeping.spare_amphora_pool_size
        curr_spare_cnt = self.vthunder_repo.get_spare_vthunder_count(session)
        LOG.debug("Required Spare vThunder count : %d", conf_spare_cnt)
        LOG.debug("Current Spare vThunder count : %d", curr_spare_cnt)
        diff_count = conf_spare_cnt - curr_spare_cnt

        # When the current spare amphora is less than required
        if diff_count > 0:
            LOG.info("Initiating creation of %d spare amphora.", diff_count)

            # Call Amphora Create Flow diff_count times
            with futures.ThreadPoolExecutor(
                    max_workers=CONF.a10_house_keeping.spare_amphora_pool_size
            ) as executor:
                for i in range(1, diff_count + 1):
                    LOG.debug("Starting amphorae number %d ...", i)
                    executor.submit(self.cw.create_amphora)
        else:
            LOG.debug("Current spare vThunder count satisfies the requirement")


class DatabaseCleanup(object):
    def __init__(self):
        self.vthunder_repo = a10repo.VThunderRepository()
        self.lb_repo = a10repo.LoadBalancerRepository()

    def delete_old_amphorae(self):
        """Checks the DB for old amphora and deletes them based on its age."""
        exp_age = datetime.timedelta(
            seconds=CONF.a10_house_keeping.amphora_expiry_age)

        session = db_api.get_session()
        amp_ids = self.vthunder_repo.get_all_deleted_expiring(session,
                                                              exp_age=exp_age)
        LOG.info('VThunder ids: %s', amp_ids)

        for amp_id in amp_ids:
            LOG.info('Attempting to purge db record for VThunder ID: %s',
                     amp_id)
            self.vthunder_repo.delete(session, id=amp_id)
            LOG.info('Purged db record for Amphora ID: %s', amp_id)

    def cleanup_load_balancers(self):
        """Checks the DB for old load balancers and triggers their removal."""
        exp_age = datetime.timedelta(
            seconds=CONF.a10_house_keeping.load_balancer_expiry_age)

        session = db_api.get_session()
        lb_ids = self.lb_repo.get_all_deleted_expiring(session,
                                                       exp_age=exp_age)
        LOG.info('Load balancer ids: %s', lb_ids)
        for lb_id in lb_ids:
            LOG.info('Attempting to delete load balancer id : %s', lb_id)
            self.lb_repo.delete(session, id=lb_id)
            LOG.info('Deleted load balancer id : %s', lb_id)


class WriteMemory(object):

    def __init__(self):
        self.prev_run_time = None
        self.thunder_repo = a10repo.VThunderRepository()
        self.cw = cw.A10ControllerWorker()

    def perform_memory_writes(self):
        write_interval = datetime.timedelta(seconds=CONF.a10_house_keeping.write_mem_interval)
        curr_time_stamp = dt_funcs.utcnow()
        expiry_time = curr_time_stamp - write_interval
        if (self.prev_run_time and int(self.prev_run_time.strftime("%s")) <
                int(expiry_time.strftime("%s"))):
            LOG.debug("Previous write memory thread ran at %s: ", str(self.prev_run_time))
            expiry_time = self.prev_run_time
        thunders = self.thunder_repo.get_recently_updated_thunders(db_api.get_session(),
                                                                   expiry_time=expiry_time)
        ip_partition_list = set()
        thunder_list = []
        for thunder in thunders:
            ip_partition = str(thunder.ip_address) + ":" + str(thunder.partition_name)
            if ip_partition not in ip_partition_list:
                ip_partition_list.add(ip_partition)
                thunder_list.append(thunder)

        self.prev_run_time = curr_time_stamp

        if thunder_list:
            LOG.info("Write Memory for Thunders : %s", list(ip_partition_list))
            self.cw.perform_write_memory(thunder_list)
            LOG.info("Finished running write memory for {} thunders...".format(len(thunder_list)))
        else:
            LOG.warning("No thunders found that are recently updated."
                        " Not performing write memory...")
