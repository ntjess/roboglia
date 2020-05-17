import pytest
import logging
import time
import yaml

from roboglia.utils import register_class, unregister_class, registered_classes, get_registered_class
from roboglia.utils import check_key, check_options, check_type, check_not_empty

from roboglia.base import BaseRobot, BaseDevice, BaseBus, BaseRegister
from roboglia.base import RegisterWithConversion, RegisterWithThreshold
from roboglia.base import BaseThread

from roboglia.dynamixel import DynamixelBus
from roboglia.dynamixel import DynamixelAXBaudRateRegister
from roboglia.dynamixel import DynamixelAXComplianceSlopeRegister
from roboglia.dynamixel import DynamixelXLBaudRateRegister

from roboglia.i2c import SharedI2CBus

# format = '%(asctime)s %(levelname)-7s %(threadName)-18s %(name)-32s %(message)s'
# logging.basicConfig(format=format, 
#                     # file = 'test.log', 
#                     level=60)    # silent
logger = logging.getLogger(__name__)



class TestMockRobot:

    @pytest.fixture
    def mock_robot(self):   
        robot = BaseRobot.from_yaml('tests/dummy_robot.yml')
        robot.start()
        yield robot
        robot.stop()

    def test_robot_from_yaml(self, mock_robot):
        mock_robot.stop()       # to avoid conflicts on the bus
        new_robot = BaseRobot.from_yaml('tests/dummy_robot.yml')
        new_robot.start()
        new_robot.syncs['write'].start()
        time.sleep(2)           # for loops to run
        new_robot.stop()
        mock_robot.start()      # restart for other cases

    def test_device_str(self, mock_robot):
        rep = str(mock_robot.devices['d01'])
        assert 'd01' in rep
        assert 'busA' in rep
        assert 'enable_device' in rep

    def test_register_with_conversion(self, mock_robot):
        reg = mock_robot.devices['d03'].desired_pos
        assert isinstance(reg, RegisterWithConversion)
        reg.value = 100
        assert abs(reg.value - 100) < 0.1
        exp_int = 100 * reg.factor + reg.offset
        assert (reg.int_value - exp_int) <=1

    def test_register_with_threshold(self, mock_robot):
        reg = mock_robot.devices['d03'].writeable_current_load
        assert isinstance(reg, RegisterWithThreshold)
        assert not reg.sync
        reg.value = 50
        assert abs(reg.value - 50) < 0.1
        exp_int = 100 * reg.factor
        assert (reg.int_value - exp_int) <=1
        reg.value = -50
        assert abs(reg.value + 50) < 0.1
        exp_int = 100 * reg.factor + reg.threshold
        assert (reg.int_value - exp_int) <=1
         

    def test_register_read_only(self, mock_robot, caplog):
        reg = mock_robot.devices['d03'].current_pos
        assert isinstance(reg, RegisterWithConversion)
        caplog.clear()
        reg.value = 100
        assert len(caplog.records) == 1
        assert 'attempted to write in RO register current_pos' in caplog.text

    def test_sync_pause_resume(self, mock_robot):
        write_sync = mock_robot.syncs['write']
        write_sync.start()
        assert write_sync.started
        assert write_sync.running
        assert not write_sync.paused
        assert not write_sync.stopped
        write_sync.pause()
        assert write_sync.started
        assert not write_sync.running
        assert write_sync.paused
        assert not write_sync.stopped
        time.sleep(0.5)
        write_sync.resume()
        assert write_sync.started
        assert write_sync.running
        assert not write_sync.paused
        assert not write_sync.stopped        
        write_sync.stop()
        assert not write_sync.started
        assert not write_sync.running
        assert not write_sync.paused
        assert write_sync.stopped          

    def test_sync_start_restart(self, mock_robot):
        write_sync = mock_robot.syncs['write']
        assert not write_sync.started
        assert not write_sync.running
        assert not write_sync.paused
        assert write_sync.stopped 
        # re-stop
        write_sync.stop()
        assert not write_sync.started
        assert not write_sync.running
        assert not write_sync.paused
        assert write_sync.stopped
        # start
        write_sync.start()
        assert write_sync.started
        assert write_sync.running
        assert not write_sync.paused
        assert not write_sync.stopped
        # re-start
        write_sync.start()
        assert write_sync.started
        assert write_sync.running
        assert not write_sync.paused
        assert not write_sync.stopped
        write_sync.stop()

    def test_loop_warning_review(self, mock_robot):
        read_sync = mock_robot.syncs['read']
        assert read_sync.warning == 0.9     # default
        read_sync.warning = 0.95
        assert read_sync.warning == 0.95
        # percentage set
        read_sync.warning = 90
        assert read_sync.warning == 0.9
        assert read_sync.review == 1.0      # default
        assert read_sync.frequency == 100

    # def test_sync_with_closed_bus(self, mock_robot, caplog):
    #     write_sync = mock_robot.syncs['write']
    #     assert write_sync.stopped
    #     bus = write_sync.bus
    #     if bus.is_open:
    #         bus.close()
    #     assert not bus.is_open
    #     caplog.clear()
    #     write_sync.start()
    #     assert len(caplog.records) == 1
    #     assert 'attempt to start with a bus not open' in caplog.text
    #     assert write_sync.stopped
    #     # now set things back
    #     bus.open()
    #     assert bus.is_open

    def test_joint_info(self, mock_robot):
        j = mock_robot.joints['pan']
        d = mock_robot.devices['d01']
        assert j.position_read_register == d.current_pos
        assert j.position_write_register == d.desired_pos
        assert j.activate_register == d.enable_device
        assert j.velocity_read_register == d.current_speed
        assert j.velocity_write_register == d.desired_speed
        assert j.load_read_register == d.current_load
        assert j.load_write_register == d.desired_load
        assert j.active

    def test_joint_value(self, mock_robot):
        tilt = mock_robot.joints['tilt']
        d02 = mock_robot.devices['d02']
        # joint is 'inverse'
        assert tilt.position == - d02.current_pos.value + tilt.offset
        assert tilt.velocity ==  - d02.current_speed.value
        assert tilt.load == - d02.current_load.value
        # setter
        tilt.position = 10
        tilt.velocity = 20
        tilt.load = 50
        assert abs(tilt.desired_position - 10) < 0.2
        assert abs(tilt.desired_velocity - 20) < 0.2
        assert abs(tilt.desired_load - 50) < 0.2

    def test_joint_min_max(self, mock_robot):
        # check min and max
        pan = mock_robot.joints['pan']
        minv, maxv = pan.range
        pan.position = 50
        assert abs(pan.desired_position - maxv) < 0.2
        pan.position = -50
        assert abs(pan.desired_position - minv) < 0.2

    def test_joint_repr(self, mock_robot):
        pan = mock_robot.joints['pan']
        pan_str = str(pan)
        assert pan.name in pan_str
        assert 'p=' in pan_str
        assert 'v=' in pan_str
        assert 'l=' in pan_str

    def test_sensor_info(self, mock_robot):
        s = mock_robot.sensors['bus_voltage']
        d = mock_robot.devices['d01']
        assert s.device == d
        assert s.read_register == d.current_voltage
        assert s.activate_register is None
        assert s.active
        assert s.mask is None
        assert s.offset == 0
        assert not s.inverse
        assert s.auto_activate

    def test_sensor_value(self, mock_robot):
        s = mock_robot.sensors['bus_voltage']
        d = mock_robot.devices['d01']
        assert s.value == d.current_voltage.value

        """This doesn't work fine as closing a bus will crash a
        sync run that is using it."""
    # def test_bus_operate_on_close(self, mock_robot, caplog):
    #     bus = mock_robot.buses['busA']
    #     if bus.is_open:
    #         bus.close()
    #     assert not bus.is_open
    #     dev = mock_robot.devices['d01']
    #     caplog.clear()
    #     bus.read(dev, dev.current_pos)
    #     assert len(caplog.records) == 1
    #     assert 'attempt to read from a closed bus' in caplog.text
    #     bus.write(dev, dev.desired_pos, 10)
    #     assert len(caplog.records) == 2
    #     assert ('attempt to write to closed bus' in caplog.text)
    #     # reset bus
    #     bus.open()
    #     assert bus.is_open
 
    def test_bus_repr(self, mock_robot):
        dev = mock_robot.devices['d01']
        for register in dev.registers.values():
            register.read()
        str_repr = str(mock_robot.buses['busA'])
        assert f'Device {dev.dev_id}' in str_repr
        for register in dev.registers.values():
            if not register.sync:
                assert str(register.address) in str_repr
                assert str(register.int_value) in str_repr

    def test_bus_acquire(self, mock_robot, caplog):
        dev = mock_robot.devices['d01']
        bus = mock_robot.buses['busA']
        # stop syncs to avoid interference (additional messages)
        for sync in mock_robot.syncs.values():
            sync.stop()
        bus.can_use()      # lock the bus
        # read
        caplog.clear()
        bus.read(dev.current_pos)
        assert len(caplog.records) == 1
        assert 'failed to acquire bus busA' in caplog.text
        # write
        caplog.clear()
        bus.write(dev.current_pos, 10)
        assert len(caplog.records) == 1
        assert 'failed to acquire bus busA' in caplog.text        
        # release bus
        bus.stop_using()
        mock_robot.stop()

    def test_bus_small_branches(self, mock_robot, caplog):
        bus = mock_robot.buses['busA']
        # close bus used by syncs
        caplog.clear()
        bus.close()
        assert len(caplog.records) == 1
        assert 'attempted to close bus' in caplog.text
        # open bus already open
        caplog.clear()
        bus.open()
        assert len(caplog.records) == 1
        assert 'bus busA already open' in caplog.text
        # read from closed bus
        device = mock_robot.devices['d04']
        caplog.clear()
        device.delay.write()
        assert len(caplog.records) == 1
        assert 'attempt to write to closed bus' in caplog.text
        caplog.clear()
        device.model.read()
        assert len(caplog.records) == 1
        assert 'attempt to read from closed bus' in caplog.text
        # timeout
        assert bus.timeout == 0.5

    def test_thread_crash(self):
        class CrashAtRun(BaseThread):
            def run(self):
                time.sleep(0.25)
                raise OSError

        class CrashAtSetup(BaseThread):
            def setup(self):
                time.sleep(.25)
                raise OSError

        class CrashLongSetup(BaseThread):
            def setup(self):
                time.sleep(1)
                raise OSError

        thread = CrashAtRun(name='my_thread')
        thread.start()
        time.sleep(0.5)
        assert not thread.started
        assert not thread.paused

        thread = CrashAtSetup(name='my_thread', patience=0.3)
        with pytest.raises(RuntimeError) as excinfo:
            thread.start()
            time.sleep(0.5)
        assert not thread.started
        assert not thread.paused       

        thread = CrashLongSetup(name='my_thread', patience=0.3)
        with pytest.raises(RuntimeError) as excinfo:
            thread.start()
            time.sleep(0.5)
        assert not thread.started
        assert not thread.paused      

class TestUtilsFactory:

    def test_register_not_class(self):
        mess = 'You must pass a Class not an instance'
        with pytest.raises(ValueError) as excinfo:
            register_class(10)
        assert mess in str(excinfo.value)

    def test_unregister_missing_class(self):
        mess = 'not registered with the factory'
        with pytest.raises(KeyError) as excinfo:
            unregister_class('dummy')
        assert mess in str(excinfo.value)

    def test_unregister_class(self):
        class Test: pass
        register_class(Test)
        assert 'Test' in registered_classes()
        unregister_class('Test')
        assert 'Test' not in registered_classes()

    def test_get_registered_class_not_available(self):
        mess = 'not registered with the factory'
        with pytest.raises(KeyError) as excinfo:
            get_registered_class('dummy')
        assert mess in str(excinfo.value)

    def test_register_class_existing(self):
        class Test: pass
        register_class(Test)
        # again
        register_class(Test)
        assert 'Test' in registered_classes()
        unregister_class('Test')
        assert 'Test' not in registered_classes()


class TestUtilsChecks:

    def test_check_key(self):
        mess = 'specification missing'
        with pytest.raises(KeyError) as excinfo:
            check_key('key', {}, 'object', 10, logger)
        assert mess in str(excinfo.value)
        with pytest.raises(KeyError) as excinfo:
            check_key('key', {}, 'object', 10, logger, 'custom')
        assert 'custom' in str(excinfo.value)

    def test_check_type(self):
        mess = 'should be of type'
        with pytest.raises(ValueError) as excinfo:
            check_type('10', int, 'object', 10, logger)
        assert mess in str(excinfo.value)
        with pytest.raises(ValueError) as excinfo:
            check_type('10', int, 'object', 10, logger, 'custom')
        assert 'custom' in str(excinfo.value)
        with pytest.raises(ValueError) as excinfo:
            check_type('10', [int, float], 'object', 10, logger)        

    def test_check_options(self):
        mess = 'should be one of'
        with pytest.raises(ValueError) as excinfo:
            check_options(10, ['a', 'b'], 'object', 10, logger)
        assert mess in str(excinfo.value)
        with pytest.raises(ValueError) as excinfo:
            check_options(10, ['a', 'b'], 'object', 10, logger, 'custom')
        assert 'custom' in str(excinfo.value)

    def test_check_not_empty(self):
        mess = 'should not be empty'
        # string
        with pytest.raises(ValueError) as excinfo:
            check_not_empty('', 'string', 'object', 10, logger)
        assert mess in str(excinfo.value)
        # number
        with pytest.raises(ValueError) as excinfo:
            check_not_empty(0, 'integer', 'object', 10, logger)
        assert mess in str(excinfo.value)
        # list
        with pytest.raises(ValueError) as excinfo:
            check_not_empty([], 'list', 'object', 10, logger)
        assert mess in str(excinfo.value)
        # dict
        with pytest.raises(ValueError) as excinfo:
            check_not_empty({}, 'dict', 'object', 10, logger)
        assert mess in str(excinfo.value)
        # custom message
        with pytest.raises(ValueError) as excinfo:
            check_not_empty('', 'string', 'object', 10, logger, 'custom')
        assert 'custom' in str(excinfo.value)


class TestDynamixelRobot:

    @pytest.fixture
    def mock_robot_init(self):
        with open('tests/dynamixel_robot.yml', 'r') as f:
            info_dict = yaml.load(f, Loader=yaml.FullLoader)
        yield info_dict

    @pytest.fixture
    def dummy_device(self):
        bus = BaseBus(robot='robot', port='dev')
        return BaseDevice(name='device', bus=bus, dev_id=42, model='DUMMY',
                          robot='robot')

    def test_dynamixel_robot(self, mock_robot_init):
        for name, init_dict in mock_robot_init.items():
            break
        robot = BaseRobot(name=name, **init_dict)
        robot.start()
        robot.stop()

    def test_dynamixel_write(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        dev = robot.devices['d11']
        for _ in range(100):           # so that we also hit some comm errors
            dev.temperature_limit.value = 85
            assert dev.temperature_limit.value == 85
            dev.cw_angle_limit_deg.value = 10
            assert (dev.cw_angle_limit_deg.value - 10) < 0.2
        robot.stop()

    def test_dynamixel_register_4Bytes(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        dev = robot.devices['d11']
        register = BaseRegister(name='test', device=dev, address=150, size=4,
                 access='RW')
        register.value = 100
        assert register.value == 100

    def test_dynamixel__AXBaudRateRegister(self, dummy_device, caplog):
        reg = DynamixelAXBaudRateRegister(
            name='test',
            device=dummy_device,
            address=42,
            minim=33,        # for testing branches
            maxim=66,        # for testing branches
            sync=True,       # avoids calling read / write
            access='RW'      # so we can change it!
        )
        reg.value = 1000000
        assert reg.value == 1000000
        assert reg.int_value == 1
        # wrong value > log error
        caplog.clear()
        reg.value = 99
        assert len(caplog.records) == 1
        assert 'attempt to write a non supported for AX baud' in caplog.text


    def test_dynamixel__AXComplianceSlopeRegister(self, dummy_device):
        reg = DynamixelAXComplianceSlopeRegister(
            name='test',
            device=dummy_device,
            address=42,
            maxim=66,        # for testing branches
            sync=True,       # avoids calling read / write
            access='RW'      # so we can change it!
        )
        reg.value = 7
        assert reg.value == 7
        assert reg.int_value == 128


    def test_dynamixel__XLBaudRateRegister(self, dummy_device, caplog):
        reg = DynamixelXLBaudRateRegister(
            name='test',
            device=dummy_device,
            address=42,
            minim=33,        # for testing branches
            maxim=66,        # for testing branches
            sync=True,       # avoids calling read / write
            access='RW'      # so we can change it!
        )
        reg.value = 1000000
        assert reg.value == 1000000
        assert reg.int_value == 3
        # wrong value > log error
        caplog.clear()
        reg.value = 99
        assert len(caplog.records) == 1
        assert 'attempt to write a non supported for XL baud' in caplog.text

    def test_open_device_with_sync_items(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        dev = robot.devices['d11']
        dev.present_position_deg.sync = True
        dev.open()
        robot.stop()

    def test_dynamixel_syncwrite(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.syncs['syncwrite'].start()
        time.sleep(1)
        robot.stop()

    def test_dynamixel_syncread(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.syncs['syncread'].start()
        time.sleep(1)
        robot.stop()

    def test_dynamixel_bulkwrite(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.syncs['bulkwrite'].start()
        time.sleep(1)
        robot.stop()

    def test_dynamixel_bulkread(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.syncs['bulkread'].start()
        time.sleep(1)
        robot.stop()

    def test_protocol1_syncread(self, mock_robot_init):
        mock_robot_init['dynamixel']['buses']['ttys1']['protocol'] = 1.0
        # we remove the bulkwrite so that the error will refer to syncread
        del mock_robot_init['dynamixel']['syncs']['bulkwrite']
        with pytest.raises(ValueError) as excinfo:
            _ = BaseRobot(**mock_robot_init['dynamixel'])
        assert 'SyncRead only supported for Dynamixel Protocol 2.0' \
            in str(excinfo.value)

    def test_protocol1_bulkwrite(self, mock_robot_init):
        mock_robot_init['dynamixel']['buses']['ttys1']['protocol'] = 1.0
        # we remove the bulkwrite so that the error will refer to syncread
        del mock_robot_init['dynamixel']['syncs']['syncread']
        with pytest.raises(ValueError) as excinfo:
            _ = BaseRobot(**mock_robot_init['dynamixel'])
        assert 'BulkWrite only supported for Dynamixel Protocol 2.0' \
            in str(excinfo.value)

    def test_dynamixel_scan(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        ids = robot.buses['ttys1'].scan()
        assert 11 in ids
        assert 12 in ids
        robot.stop()

    def test_dynamixel_ping(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        assert robot.buses['ttys1'].ping(11) == True
        robot.stop()

    # def test_dynamixel_bus_set_port_handler(self, mock_robot_init):
    #     robot = BaseRobot(mock_robot_init)
    #     mess = 'you can use the setter only with MockBus'
    #     with pytest.raises(ValueError) as excinfo:
    #         robot.buses['ttys1'].port_handler = 'dummy'
    #     assert mess in str(excinfo.value)
    #     robot.stop()
    
    # def test_dynamixel_bus_set_packet_handler(self, mock_robot_init):
    #     robot = BaseRobot(mock_robot_init)
    #     mess = 'you can use the setter only with MockPacketHandler'
    #     with pytest.raises(ValueError) as excinfo:
    #         robot.buses['ttys1'].packet_handler = 'dummy'
    #     assert mess in str(excinfo.value)
    #     robot.stop()

    def test_dynamixel_bus_params(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        assert robot.buses['ttys1'].baudrate == 19200
        assert not robot.buses['ttys1'].rs485
        robot.stop()

    def test_dynamixel_bus_closed(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        bus = robot.buses['ttys1']
        # ping
        caplog.clear()
        bus.ping(11)
        assert len(caplog.records) == 1
        assert 'ping invoked with a bus not opened' in caplog.text
        # scan
        caplog.clear()
        bus.scan(range(10))
        assert len(caplog.records) == 1
        assert 'scan invoked with a bus not opened' in caplog.text
        # read
        dev = robot.devices['d11']
        caplog.clear()
        bus.read(dev.return_delay_time)
        assert len(caplog.records) == 1
        assert 'attempt to use closed bus ttys1' in caplog.text
        # write
        caplog.clear()
        bus.write(dev.return_delay_time, 10)
        assert len(caplog.records) == 1
        assert 'attempt to use closed bus ttys1' in caplog.text
        robot.stop()


    def test_dynamixel_bus_acquire(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        dev = robot.devices['d11']
        bus = robot.buses['ttys1']
        bus.can_use()      # lock the bus
        # read
        caplog.clear()
        bus.read(dev.return_delay_time)
        assert len(caplog.records) == 1
        assert 'failed to acquire bus ttys1' in caplog.text
        # write
        caplog.clear()
        bus.write(dev.return_delay_time, 10)
        assert len(caplog.records) == 1
        assert 'failed to acquire bus ttys1' in caplog.text
        # release bus
        bus.stop_using()
        robot.stop()

    def test_dynamixel_bus_acquire_syncwrite(self, mock_robot_init, caplog):
        # syncs
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.buses['ttys1'].can_use()      # lock the bus
        caplog.clear()
        robot.syncs['syncwrite'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        robot.syncs['syncwrite'].stop()
        # release bus
        robot.buses['ttys1'].stop_using()
        robot.stop()

    def test_dynamixel_bus_acquire_syncread(self, mock_robot_init, caplog):
        # syncs
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.buses['ttys1'].can_use()      # lock the bus
        caplog.clear()
        robot.syncs['syncread'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        robot.syncs['syncread'].stop()
        # release bus
        robot.buses['ttys1'].stop_using()
        robot.stop()

    def test_dynamixel_bus_acquire_bulkwrite(self, mock_robot_init, caplog):
        # syncs
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.buses['ttys1'].can_use()      # lock the bus
        caplog.clear()
        robot.syncs['bulkwrite'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        robot.syncs['bulkwrite'].stop()
        # release bus
        robot.buses['ttys1'].stop_using()
        robot.stop()

    def test_dynamixel_bus_acquire_bulkread(self, mock_robot_init, caplog):
        # syncs
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        robot.start()
        robot.buses['ttys1'].can_use()      # lock the bus
        caplog.clear()
        robot.syncs['bulkread'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus ttys1' in caplog.text
        robot.syncs['bulkread'].stop()
        # release bus
        robot.buses['ttys1'].stop_using()
        robot.stop()

    def test_dynamixel_register_low_endian(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['dynamixel'])
        dev = robot.devices['d11']
        assert dev.register_low_endian(123, 4) == [123, 0, 0, 0]
        num = 12 * 256 + 42
        assert dev.register_low_endian(num, 4) == [42, 12, 0, 0]
        num = 39 * 65536 + 12 * 256 + 42
        assert dev.register_low_endian(num, 4) == [42, 12, 39, 0]
        num = 45 * 16777216 + 39 * 65536 + 12 * 256 + 42
        assert dev.register_low_endian(num, 4) == [42, 12, 39, 45]
        caplog.clear()
        _ = dev.register_low_endian(num, 6)
        assert len(caplog.records) == 1
        assert 'Unexpected register size' in caplog.text

class TestI2CRobot:

    @pytest.fixture
    def mock_robot_init(self):
        with open('tests/i2c_robot.yml', 'r') as f:
            info_dict = yaml.load(f, Loader=yaml.FullLoader)
        yield info_dict

    def test_i2c_robot_bus_error(self, mock_robot_init, caplog):
        mock_robot_init['i2crobot']['buses']['i2c2']['mock'] = False
        mock_robot_init['i2crobot']['buses']['i2c2']['auto'] = False
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        caplog.clear()
        robot.buses['i2c2'].open()
        assert len(caplog.records) == 2
        assert 'failed to open I2C bus' in caplog.text
        # caplog.clear()
        # robot.buses['i2c2'].close()
        # assert len(caplog.records) == 2
        # assert 'failed to close I2C bus' in caplog.text

    def test_i2c_robot(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        dev = robot.devices['imu']
        # 1 Byte registers
        for _ in range(5):              # to account for possible comm errs
            dev.byte_xl_x.value = 20
            assert dev.byte_xl_x.value == 20
            # word register
            dev.word_xl_x.value = 12345
            assert dev.word_xl_x.value == 12345      
        robot.stop()

    def test_i2c_sensorXYZ(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        s = robot.sensors['gyro']
        d = robot.devices['imu']
        assert s.device == d
        assert s.x_register == d. word_g_x
        assert s.y_register == d. word_g_y
        assert s.z_register == d. word_g_z
        assert s.activate_register is None
        assert s.active
        assert s.x_offset == 0
        assert s.x_inverse
        assert s.y_offset == 256
        assert not s.y_inverse
        assert s.z_offset == 1024
        assert s.z_inverse        
        assert s.auto_activate

    def test_i2c_sensorXYZ_value(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        s = robot.sensors['gyro']
        d = robot.devices['imu']
        exp_x = - d.word_g_x.value
        exp_y = d.word_g_y.value + 256
        exp_z = - d.word_g_z.value + 1024
        assert s.x == exp_x
        assert s.y == exp_y
        assert s.z == exp_z
        assert s.value == (exp_x, exp_y, exp_z)

    def test_i2c_bus_closed(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        dev = robot.devices['imu']
        # write to closed bus
        caplog.clear()
        dev.byte_xl_x.value = 20
        assert len(caplog.records) == 1
        assert 'attempted to write to a closed bus' in caplog.text
        # read from closed bus
        caplog.clear()
        _ = dev.byte_xl_x.value
        assert len(caplog.records) == 1
        assert 'attempted to read from a closed bus' in caplog.text

    def test_i2c_read_loop(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        robot.syncs['read_g'].start()
        time.sleep(1)
        robot.stop()

    def test_i2c_write_loop(self, mock_robot_init):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        robot.syncs['write_xl'].start()
        time.sleep(1)
        robot.stop()

    def test_i2c_loop_failed_acquire(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        # lock the bus
        robot.buses['i2c2'].can_use()
        # read
        caplog.clear()
        robot.syncs['read_g'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus' in caplog.text
        robot.syncs['read_g'].stop()    
        # write
        caplog.clear()
        robot.syncs['write_xl'].start()
        time.sleep(1)
        assert len(caplog.records) >= 1
        assert 'failed to acquire bus' in caplog.text
        robot.syncs['read_g'].stop()    

    def test_i2c_sharedbus_closed(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        # we haven't started the bus
        # read
        caplog.clear()
        robot.syncs['read_g'].start()
        assert len(caplog.records) == 1
        assert 'attempt to start with a bus not open' in caplog.text
        robot.syncs['read_g'].stop()    
        # write
        caplog.clear()
        robot.syncs['write_xl'].start()
        assert len(caplog.records) == 1
        assert 'attempt to start with a bus not open' in caplog.text
        robot.syncs['read_g'].stop()

    def test_i2c_write2_with_errors(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        robot.start()
        device = robot.devices['imu']
        for _ in range(20):     # so that we also get some errors
            device.word_control_2.value = 0x2121
        assert device.word_control_2.value == 0x2121

    def test_i2c_closed_bus(self, mock_robot_init, caplog):
        robot = BaseRobot(**mock_robot_init['i2crobot'])
        device = robot.devices['imu']
        caplog.clear()
        _ = device.word_control_2.value
        assert len(caplog.records) >= 1
        assert 'attempted to read from a closed bus' in caplog.text
        caplog.clear()
        device.word_control_2.value = 0x4242
        assert len(caplog.records) >= 1
        assert 'attempted to write to a closed bus' in caplog.text
        bus = robot.buses['i2c2']
        caplog.clear()
        _ = bus.read_block_data(1, 1, 6)
        assert len(caplog.records) >= 1
        assert 'attempted to read from a closed bus' in caplog.text
        caplog.clear()
        bus.write_block_data(1, 1, 6, [1,2,3,4,5,6])
        assert len(caplog.records) >= 1
        assert 'attempted to write to a closed bus' in caplog.text
