import unittest
import sys
import logging
import yaml

logging.basicConfig(level=60)       # silent

from roboglia.base import BaseRobot

class TestRobot(unittest.TestCase):

    def setUp(self):
        self.robot = yaml.load("""
            buses:
                - name: busA
                  class: FileBus
                  port: /tmp/busA.log

            devices:
                - name: d01
                  class: BaseDevice
                  bus: busA
                  id: 1
                  model: DUMMY
        """, Loader=yaml.FullLoader)

    def test_mock_robot(self):
        _ = BaseRobot(self.robot)



if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(TestRobot('test_mock_robot'))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2)
    runner.run(suite)
