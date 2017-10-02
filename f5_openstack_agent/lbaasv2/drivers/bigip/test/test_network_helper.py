#!/usr/bin/env python
# Copyright 2017 F5 Networks Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import pytest

from mock import Mock
from mock import patch
from requests import HTTPError

import f5_openstack_agent.lbaasv2.drivers.bigip.network_helper


class TestNetworkHelperConstructor(object):
    @staticmethod
    @pytest.fixture
    @patch('f5_openstack_agent.lbaasv2.drivers.bigip.network_helper.'
           'NetworkHelper.__init__')
    def fully_mocked_target(init):
        init.return_value = None
        return f5_openstack_agent.lbaasv2.drivers.bigip.network_helper.\
            NetworkHelper()


class TestNetworkHelperBuilder(TestNetworkHelperConstructor):
    @pytest.fixture
    def mock_logger(self, request):
        request.addfinalizer(self.cleanup)
        self.freeze_logger = \
            f5_openstack_agent.lbaasv2.drivers.bigip.network_helper.LOG
        logger = Mock()
        self.logger = logger
        f5_openstack_agent.lbaasv2.drivers.bigip.network_helper.LOG = logger
        return logger

    def cleanup(self):
        if hasattr(self, 'freeze_logger'):
            f5_openstack_agent.lbaasv2.drivers.bigip.network_helper.LOG = \
                self.freeze_logger


class TestNetworkHelper(TestNetworkHelperBuilder):
    def test_get_virtual_service_insertion(self, fully_mocked_target,
                                           mock_logger):
        def setup_target(target):
            target.split_addr_port = Mock()

        def make_bigip():
            bigip = Mock()
            vip_port = '1010'
            vaddr = '192.168.1.1'
            netmask = '255.255.255.0'
            protocol = 'HTTP'
            lb_id = 'TEST_FOO'
            fwd_name = 'hello'
            name = 'name'
            dest = "{}/{}:{}".format(fwd_name, lb_id, vip_port)
            partition = 'Common'
            va = Mock()
            vs = Mock()
            bigip.tm.ltm.virtuals.get_collection.return_value = \
                [vs]
            vs.destination = dest
            vs.mask = netmask
            vs.ipProtocol = protocol
            vs.name = name
            bigip.tm.ltm.virtual_address_s.virtual_address.load.return_value \
                = va
            va.raw = dict(address=vaddr)
            bigip.vip_port = vip_port
            bigip.vaddr = vaddr
            bigip.netmask = netmask
            bigip.protocol = protocol
            bigip.lb_id = lb_id
            bigip.fwd_name = fwd_name
            bigip.name = name
            bigip.dest = dest
            bigip.partition = partition
            return bigip

        def positive_load_va(target):
            setup_target(target)
            bigip = make_bigip()
            # local, test variables...
            target.split_addr_port.return_value = \
                tuple([bigip.lb_id, bigip.vip_port])
            # bigip mocking...
            expected = [{bigip.name: dict(address=bigip.vaddr,
                                          netmask=bigip.netmask,
                                          protocol=bigip.protocol,
                                          port=bigip.vip_port)}]
            # Test code...
            assert target.get_virtual_service_insertion(
                bigip, partition='Common') == expected
            target.split_addr_port.assert_called_once_with(
                "{}:{}".format(bigip.lb_id, bigip.vip_port))
            bigip.tm.ltm.virtuals.get_collection.assert_called_once_with(
                partition=bigip.partition)
            bigip.tm.ltm.virtual_address_s.virtual_address.load.\
                assert_called_once_with(
                    name=bigip.lb_id, partition=bigip.partition)

        def negative_load_va(target):
            setup_target(target)
            bigip = make_bigip()
            bigip.tm.ltm.virtual_address_s.virtual_address.load.\
                side_effect = AssertionError('foo')
            target.split_addr_port.return_value = \
                tuple([bigip.lb_id, bigip.vip_port])
            with pytest.raises(AssertionError):
                target.get_virtual_service_insertion(
                    bigip, partition=bigip.partition)

        def positive_w_exception(target):
            setup_target(target)
            bigip = make_bigip()
            http_error = HTTPError('foo')
            http_error.response = Mock()
            http_error.response.status_code = 404
            bigip.tm.ltm.virtual_address_s.virtual_address.load.side_effect = \
                http_error
            target.split_addr_port.return_value = \
                tuple([bigip.lb_id, bigip.vip_port])
            expected = \
                [{bigip.name: dict(address=bigip.lb_id,
                                   netmask=bigip.netmask,
                                   protocol=bigip.protocol,
                                   port=bigip.vip_port)}]
            assert target.get_virtual_service_insertion(
                bigip, partition=bigip.partition) == expected

        positive_load_va(fully_mocked_target)
        negative_load_va(self.fully_mocked_target())
        positive_w_exception(self.fully_mocked_target())