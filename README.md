# raspberry-temperature
Reads and logs DS18B20 Temperature sensors via 1-wire interface

Values are are read every X seconds and written to USB stick every Y minutes.

## Configuration:

STORAGE_DEVICE=/dev/sda1

MOUNT_POINT=/tmp/stick

DIRECTORY=mittaukset

\# temperature sensor read time interval in seconds

TEMPERATURE_READ_INTERVAL=30

\# write interval in minutes 

WRITE_INTERVAL=2

TEST=N

SEPARATOR=,

## Installation

Install kernel modules:

Add line: dtoverlay=w1-gpio,gpiopin=4 to /boot/config and reboot raspberry.

If some other gpio pin is used, change gpiopin attribute accordingly.

Copy files to following locations:
* /usr/lib/systemd/system/temperature.service
* /etc/default/temperature
* /usr/share/temperature/start.sh
* /usr/share/temperature/reader.py

start service:

sudo systemctl enable temperature

sudo systemctl start temperature

## Results

Results are written to device DEVICE directory DIRECTORY into a file. Each day has own file.
File contains lines \<date>	\<result1>	\<resultN>
The number of result colums depends on how many temperature sensors are available.

