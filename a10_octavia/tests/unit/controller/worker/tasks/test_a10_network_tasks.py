#    Copyright 2020, A10 Networks
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


import copy
import imp
try:
    from unittest import mock
except ImportError:
    import mock

from octavia.common import data_models as o_data_models
from octavia.network import data_models as o_net_data_models

from a10_octavia.common import data_models
from a10_octavia.common import exceptions
from a10_octavia.controller.worker.tasks import a10_network_tasks
from a10_octavia.tests.common import a10constants
from a10_octavia.tests.unit import base

MEMBER = o_data_models.Member()
VTHUNDER = data_models.VThunder()
SUBNET = o_net_data_models.Subnet()
PORT = o_net_data_models.Port()
VRID = data_models.VRID()


class MockIP(object):
    def __init__(self, ip_address):
        self.ip_address = ip_address


class TestNetworkTasks(base.BaseTaskTestCase):

    def setUp(self):
        super(TestNetworkTasks, self).setUp()
        imp.reload(a10_network_tasks)
        patcher = mock.patch(
            'a10_octavia.controller.worker.tasks.a10_network_tasks.BaseNetworkTask.network_driver')
        self.network_driver_mock = patcher.start()
        self.client_mock = mock.Mock()

# 1 no vrid and no floating ip (shared)
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project', return_value=None)
    def test_handle_vrrp_fip_with_no_vrid_no_fip(self, mock_utils):
        network_task = a10_network_tasks.HandleVRIDFloatingIP()
        result = network_task.execute(VTHUNDER, MEMBER, None)
        self.assertEqual(result, None)

# 2.a (SHARED_PARTITION) NO VRIP, FIP provided
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_1)
    @mock.patch('a10_octavia.common.utils.get_patched_ip_address',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_1)
    def test_handle_vrid_fip_with_no_vrid_but_fip_given_in_shared_partition(
            self, mock_patched_ip, mock_floating_ip):
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FLOATING_IP_1))
        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.network_driver_mock.create_port.return_value = port
        mock_network_task.execute(VTHUNDER, member, None)
        self.network_driver_mock.create_port.assert_called_with(
            subnet.network_id, member.subnet_id, fixed_ip=a10constants.MOCK_VRID_FLOATING_IP_1)
        self.client_mock.vrrpa.update.assert_called_with(
            0, floating_ip=a10constants.MOCK_VRID_FLOATING_IP_1)

# 2.b (SPECIFIC PARTITION) NO VRIP, FIP provided
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_1)
    @mock.patch('a10_octavia.common.utils.get_patched_ip_address',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_1)
    def test_handle_vrid_fip_with_no_vrid_but_fip_given_in_specific_partition(
            self, mock_patched_ip, get_floating_ip):
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FLOATING_IP_1))
        vthunder = copy.deepcopy(VTHUNDER)
        vthunder.partition_name = 'partition_1'
        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.network_driver_mock.create_port.return_value = port
        mock_network_task.execute(vthunder, member, None)
        self.network_driver_mock.create_port.assert_called_with(
            subnet.network_id, member.subnet_id, fixed_ip=a10constants.MOCK_VRID_FLOATING_IP_1)
        self.client_mock.vrrpa.update.assert_called_with(
            0, floating_ip=a10constants.MOCK_VRID_FLOATING_IP_1, is_partition=True)

# 3.a (SHARED_PARTITION) NO VRID, provided "DHCP" as FIP
    @mock.patch('a10_octavia.common.utils.check_ip_in_subnet_range', return_value=False)
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project', return_value='dhcp')
    def test_handle_vrid_fip_with_no_vrid_but_dhcp_fip_given_in_shared_partition(
            self, get_floating_ip, check_subnet):
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FLOATING_IP_1))
        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.network_driver_mock.create_port.return_value = port
        mock_network_task.execute(VTHUNDER, member, None)
        self.network_driver_mock.create_port.assert_called_with(
            subnet.network_id, member.subnet_id)
        self.client_mock.vrrpa.update.assert_called_with(
            0, floating_ip=a10constants.MOCK_VRID_FLOATING_IP_1)

# 3.b (SPECIFIC _PARTITION) NO VRID, provided "DHCP" as FIP
    @mock.patch('a10_octavia.common.utils.check_ip_in_subnet_range', return_value=False)
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project', return_value='dhcp')
    def test_handle_vrid_fip_with_no_vrid_but_dhcp_fip_given_in_specific_partition(
            self, get_floating_ip, check_subnet):
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FLOATING_IP_1))
        vthunder = copy.deepcopy(VTHUNDER)
        vthunder.partition_name = 'partition_1'
        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.network_driver_mock.create_port.return_value = port
        mock_network_task.execute(vthunder, member, None)
        self.network_driver_mock.create_port.assert_called_with(
            subnet.network_id, member.subnet_id)
        self.client_mock.vrrpa.update.assert_called_with(
            0, floating_ip=a10constants.MOCK_VRID_FLOATING_IP_1, is_partition=True)

# 4 vrid given and no floating ip provided
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project', return_value=None)
    def test_handle_vrrp_fip_with_vrid_given_but_no_fip(self, mock_utils):
        network_task = a10_network_tasks.HandleVRIDFloatingIP()
        result = network_task.execute(VTHUNDER, MEMBER, VRID)
        self.assertEqual(result, None)

# 5 VRID Provided, same FIP as VRID
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_1)
    @mock.patch('a10_octavia.common.utils.get_patched_ip_address',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_1)
    def test_handle_vrid_fip_with_vrid_and_fip_both_given_same(
            self, mock_patched_ip, get_floating_ip):
        vrid = copy.deepcopy(VRID)
        vrid.vrid_floating_ip = a10constants.MOCK_VRID_FLOATING_IP_1
        vrid.vrid = 0
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FLOATING_IP_1))
        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        mock_network_task.execute(VTHUNDER, member, vrid)
        self.network_driver_mock.create_port.assert_not_called()
        self.client_mock.vrrpa.update.assert_not_called()

# 6.a (SHARED PARTITION) VRID Provided different FIP
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_2)
    @mock.patch('a10_octavia.common.utils.get_patched_ip_address',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_2)
    def test_handle_vrid_fip_with_vrid_and_fip_given_different_in_shared_partition(
            self, mock_patched_ip, get_floating_ip):
        vrid = copy.deepcopy(VRID)
        vrid.vrid_floating_ip = a10constants.MOCK_VRID_FLOATING_IP_1
        vrid.vrid = 0
        vrid.vrid_port_id = a10constants.MOCK_VRRP_PORT_ID
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FLOATING_IP_2))
        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.network_driver_mock.create_port.return_value = port
        mock_network_task.execute(VTHUNDER, member, vrid)
        self.network_driver_mock.create_port.assert_called_with(
            subnet.network_id, member.subnet_id, fixed_ip=a10constants.MOCK_VRID_FLOATING_IP_2)
        self.client_mock.vrrpa.update.assert_called_with(
            0, floating_ip=a10constants.MOCK_VRID_FLOATING_IP_2)
        self.network_driver_mock.delete_port.assert_called_with(a10constants.MOCK_VRRP_PORT_ID)

# 6.b (SPECIFIC PARTITION) VRID Provided different FIP
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_2)
    @mock.patch('a10_octavia.common.utils.get_patched_ip_address',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_2)
    def test_handle_vrid_fip_with_vrid_and_fip_given_different_in_specific_partition(
            self, mock_patched_ip, get_floating_ip):
        vrid = copy.deepcopy(VRID)
        vrid.vrid_floating_ip = a10constants.MOCK_VRID_FLOATING_IP_1
        vrid.vrid = 0
        vrid.vrid_port_id = a10constants.MOCK_VRRP_PORT_ID
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FLOATING_IP_2))
        vthunder = copy.deepcopy(VTHUNDER)
        vthunder.partition_name = 'partition_1'
        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.network_driver_mock.create_port.return_value = port
        mock_network_task.execute(vthunder, member, vrid)
        self.network_driver_mock.create_port.assert_called_with(
            subnet.network_id, member.subnet_id, fixed_ip=a10constants.MOCK_VRID_FLOATING_IP_2)
        self.client_mock.vrrpa.update.assert_called_with(
            0, floating_ip=a10constants.MOCK_VRID_FLOATING_IP_2, is_partition=True)
        self.network_driver_mock.delete_port.assert_called_with(a10constants.MOCK_VRRP_PORT_ID)

# 7 VRID provided, FIP as DHCP from same subnet
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project', return_value='dhcp')
    def test_handle_vrid_fip_with_vrid_and_dhcp_fip_given_and_fip_is_from_same_subnet(
            self, get_floating_ip):
        vrid = copy.deepcopy(VRID)
        vrid.vrid_floating_ip = a10constants.MOCK_VRID_FLOATING_IP_1
        vrid.vrid = 0
        vrid.vrid_port_id = a10constants.MOCK_VRRP_PORT_ID
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR

        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        fip_port = mock_network_task.execute(VTHUNDER, member, vrid)
        self.network_driver_mock.create_port.assert_not_called()
        self.client_mock.vrrpa.update.assert_not_called()
        self.network_driver_mock.delete_port.assert_not_called()
        self.assertEqual(fip_port, None)

# 8.a (SHARED PARTITION) VRID provided FIP,  as DHCP from different subnet
    @mock.patch('a10_octavia.common.utils.check_ip_in_subnet_range', return_value=False)
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project', return_value='dhcp')
    def test_handle_vrid_fip_with_vrid_and_dhcp_fip_and_fip_from_diff_subnet_in_shared_partition(
            self, get_floating_ip, check_subnet):
        vrid = copy.deepcopy(VRID)
        vrid.vrid_floating_ip = a10constants.MOCK_VRID_FLOATING_IP_1
        vrid.vrid = 0
        vrid.vrid_port_id = a10constants.MOCK_VRRP_PORT_ID
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FLOATING_IP_1))

        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.network_driver_mock.create_port.return_value = port
        mock_network_task.execute(VTHUNDER, member, vrid)
        self.network_driver_mock.create_port.assert_called_with(
            subnet.network_id, member.subnet_id)
        self.client_mock.vrrpa.update.assert_called_with(
            0, floating_ip=a10constants.MOCK_VRID_FLOATING_IP_1)
        self.network_driver_mock.delete_port.assert_called_with(a10constants.MOCK_VRRP_PORT_ID)

# 8.b (SPECIFIC PARTITION) VRID provided FIP,  as DHCP from different subnet
    @mock.patch('a10_octavia.common.utils.check_ip_in_subnet_range', return_value=False)
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project', return_value='dhcp')
    def test_handle_vrid_fip_with_vrid_and_dhcp_fip_and_fip_from_diff_subnet_in_specific_partition(
            self, get_floating_ip, check_subnet):
        vrid = copy.deepcopy(VRID)
        vrid.vrid_floating_ip = a10constants.MOCK_VRID_FLOATING_IP_1
        vrid.vrid = 0
        vrid.vrid_port_id = a10constants.MOCK_VRRP_PORT_ID
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FLOATING_IP_1))
        vthunder = copy.deepcopy(VTHUNDER)
        vthunder.partition_name = 'partition_1'
        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.network_driver_mock.create_port.return_value = port
        mock_network_task.execute(vthunder, member, vrid)
        self.network_driver_mock.create_port.assert_called_with(
            subnet.network_id, member.subnet_id)
        self.client_mock.vrrpa.update.assert_called_with(
            0, floating_ip=a10constants.MOCK_VRID_FLOATING_IP_1, is_partition=True)
        self.network_driver_mock.delete_port.assert_called_with(a10constants.MOCK_VRRP_PORT_ID)


# 9 Floating IP out of range
    @mock.patch('a10_octavia.common.utils.check_ip_in_subnet_range', return_value=False)
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_1)
    @mock.patch('a10_octavia.common.utils.get_patched_ip_address',
                return_value=a10constants.MOCK_VRID_FLOATING_IP_1)
    def test_handle_vrid_fip_with_vrid_and_fip_given_and_fip_is_out_of_range(
            self, mock_patched_ip, mock_get_floating_ip, check_subnet):
        vrid = copy.deepcopy(VRID)
        vrid.vrid_floating_ip = a10constants.MOCK_VRID_FLOATING_IP_1
        vrid.vrid = 0
        vrid.vrid_port_id = a10constants.MOCK_VRRP_PORT_ID
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.assertRaises(exceptions.VRIDIPNotInSubentRangeError,
                          mock_network_task.execute, VTHUNDER, member, vrid)

# 10 partial VRID positive
    @mock.patch('a10_octavia.common.utils.get_vrid_floating_ip_for_project',
                return_value=a10constants.MOCK_VRID_PARTIAL_FLOATING_IP)
    def test_handle_vrid_fip_with_no_vrid_but_partial_fip_given(self, get_floating_ip):
        member = copy.deepcopy(MEMBER)
        member.subnet_id = a10constants.MOCK_SUBNET_ID
        subnet = copy.deepcopy(SUBNET)
        subnet.cidr = a10constants.MOCK_SUBNET_CIDR
        port = copy.deepcopy(PORT)
        port.fixed_ips.append(MockIP(a10constants.MOCK_VRID_FULL_FLOATING_IP))

        mock_network_task = a10_network_tasks.HandleVRIDFloatingIP()
        mock_network_task.axapi_client = self.client_mock
        self.network_driver_mock.get_subnet.return_value = subnet
        self.network_driver_mock.create_port.return_value = port
        mock_network_task.execute(VTHUNDER, member, None)
        self.network_driver_mock.create_port.assert_called_with(
            subnet.network_id, member.subnet_id, fixed_ip=a10constants.MOCK_VRID_FULL_FLOATING_IP)
        self.client_mock.vrrpa.update.assert_called_with(
            0, floating_ip=a10constants.MOCK_VRID_FULL_FLOATING_IP)

    def test_delete_member_vrid_port_with_both_vrid_and_non_zero_count(self):
        mock_network_task = a10_network_tasks.DeleteMemberVRIDPort()
        vrid = copy.deepcopy(VRID)
        vrid.vrid_port_id = a10constants.MOCK_VRRP_PORT_ID
        vrid.vrid = 0
        mock_network_task.axapi_client = self.client_mock
        mock_network_task.execute(VTHUNDER, vrid, 1)
        self.network_driver_mock.delete_port.assert_called_with(a10constants.MOCK_VRRP_PORT_ID)
        self.client_mock.vrrpa.delete.assert_called_with(vrid.vrid)

    def test_delete_member_vrid_port_with_zero_count_or_none_vrid(self):
        mock_network_task = a10_network_tasks.DeleteMemberVRIDPort()
        mock_network_task.axapi_client = self.client_mock
        mock_network_task.execute(VTHUNDER, None, 0)
        self.network_driver_mock.delete_port.assert_not_called()
        self.client_mock.vrrpa.delete.assert_not_called()
