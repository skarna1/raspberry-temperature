#!/usr/bin/python

import glob
import re
import sys
import os
import time
import datetime
import subprocess


class TemperatureSensor(object):
    """
    Read data from DS18B20 Temperature sensor via 1-wire interface.
    """
    _DRIVER = "/sys/bus/w1/devices/%s/w1_slave"
    _TEMP_PATTERN = re.compile("t=(-?\d+)")

    def __init__(self, sensor_id):
        self._id = sensor_id

    def _read_data(self):
        with open(self._DRIVER % (self._id, ), "r") as data_file:
            return data_file.read()

    def get_temperature(self):
        data = self._read_data()
        # data should contain 2 lines of text like this:
        # 86 01 4b 46 7f ff 0a 10 5e : crc=5e YES
        # 86 01 4b 46 7f ff 0a 10 5e t=24375
        #
        # Temperature reading is value of t= in milli-degrees C
        m = self._TEMP_PATTERN.search(data)
        if not m:
            raise IOError("Invalid data for sensor " + self._id + " data:\n" + data)
        return float(m.group(1)) / 1000.0


class MockSensor(TemperatureSensor):

    def __init__(self, sensor_id):
        super(MockSensor, self).__init__(sensor_id)         

    def _read_data(self):
        return '86 01 4b 46 7f ff 0a 10 5e : crc=5e YES\n86 01 4b 46 7f ff 0a 10 5e t=24375'


class SensorFactory(object):

    @staticmethod
    def create_sensor(sensor_id):
        if os.environ['TEST'] == "Y":
            return MockSensor(sensor_id)
        else:
            return TemperatureSensor(sensor_id)


class Reader(object):

    def __init__(self, sensors):
        self.values = []
        self.sensors = []
        for sensor_id in sensors:
            sensor = SensorFactory().create_sensor(sensor_id)
            self.sensors.append(sensor)
        self.memory_stick = MemoryStick()
        self.directory = self.memory_stick.output_directory

    def read_temperatures(self):
        temperatures = []
        retry = 0
        timestamp = time.time()
        while True:
            try:
                for sensor in self.sensors:
                    temperature = sensor.get_temperature()
                    temperatures.append(temperature)
                self.values.append((timestamp, temperatures))
                return timestamp
            except:
                time.sleep(1)
                retry +=1
                if retry > 5:
                    raise   

    def write_values(self, timestamp):
        self.memory_stick.mount() 
        subprocess.check_output('mkdir -p {}'.format(self.directory), shell=True)
        filename = self._get_filename(timestamp)
        with open(filename, "a") as out_file:
            for value in self.values:
                datastr = "\t".join(map(str, value[1]))
                datastr = datastr.replace('.', os.environ['SEPARATOR'])
                st = datetime.datetime.fromtimestamp(value[0]).strftime('%Y-%m-%d %H:%M:%S') 
                out_file.write('{}\t{}\r\n'.format(st, datastr))
        self.memory_stick.umount()
        self.values = []

    def _get_filename(self, timestamp):
        st = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        return self.directory + 'mittaus_{}.txt'.format(st) 


class NotMounted(Exception):
    def __init__(self, msg):
        super(NotMounted, self).__init__(msg)


class MemoryStick(object):

    def __init__(self):
        self.device = os.environ['STORAGE_DEVICE']
        self.mount_point = os.environ['MOUNT_POINT']
        self._output_directory = self.mount_point + '/' + os.environ['DIRECTORY'] + '/'

    def get_mount_point(self):
        cmd = 'cat /proc/mounts | grep "{} " | cut -f2 -d " "'.format(self.device)
        mount_point = subprocess.check_output(cmd, shell=True)
        if not mount_point:
            raise NotMounted('Could not read mountpoint for device {}'.format(self.device))
        return mount_point 

    def is_mounted(self):
        try:
            mount_point = self.get_mount_point()
            return True
        except NotMounted as ex:
            return False

    def umount(self):
        if self.is_mounted():
            cmd = 'sudo umount {}'.format(self.device)
            subprocess.check_output(cmd, shell=True)

    def mount(self):
        if self.is_mounted():
            return
        cmd = 'mkdir -p {}'.format(self.mount_point)
        subprocess.check_output(cmd, shell=True)
        cmd = 'sudo mount {} {}'.format(self.device, self.mount_point)
        subprocess.check_output(cmd, shell=True)

    @property 
    def output_directory(self):
        return self._output_directory

 
def main(sensors):
    timer = 0
    read_interval = int(os.environ['TEMPERATURE_READ_INTERVAL'])
    write_interval = int(os.environ['WRITE_INTERVAL']) * 60
    reader = Reader(sensors)
    reader.memory_stick.umount()
    while True:
        timestamp = reader.read_temperatures() 
        time.sleep(read_interval)
        timer += read_interval 
        if timer >= write_interval:
            try:
                reader.write_values(timestamp)
            except subprocess.CalledProcessError as ex:
                pass 
            except Exception as e:
                print >> sys.stderr, str(e)
            timer = 0

 
if __name__ == '__main__':
    sensors = [ os.path.basename(x) for x in glob.glob('/sys/bus/w1/devices/28*') ]
    main(sensors)

