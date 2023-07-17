#!/usr/bin/python3

### Configuration keys

GAUGE_KEY_NAME="voltdemort"
VOLTAGE_KEY="voltage"
CURRENT_KEY="current"
POWER_KEY="power"
FREQUENCY_KEY="frequency"
TTY="ttyUSB0"
HTTP_PORT=9097
SLEEPER=10

### Main programs starts here

import time
import json
import os
import serial as serial_interface
import signal
import sys
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu
from modbus_tk import modbus
import prometheus_client
from prometheus_client.core import GaugeMetricFamily, REGISTRY, CounterMetricFamily
from prometheus_client import start_http_server

# Serial Port Handler will be used as global var
global serial
serial = None
global bus
bus = None

# Handle signals for graceful stop
class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self, *args):
    self.kill_now = True

# Prometheus collector class
class VoltdemortCollector:
    def __init__(self):
      pass
    def collect(self):
      print("Called collect routine")
      global bus
      dict_payload = {
        VOLTAGE_KEY: 0,
        CURRENT_KEY: 0,
        POWER_KEY: 0,
        FREQUENCY_KEY: 0,
      }
      try:
        data = bus.execute(1, cst.READ_INPUT_REGISTERS, 0, 10)
        dict_payload[VOLTAGE_KEY]= data[0] / 10.0 # [V]
        dict_payload[CURRENT_KEY] = (data[1] + (data[2] << 16)) / 1000.0 # [A]
        dict_payload[POWER_KEY] = (data[3] + (data[4] << 16)) / 10.0 # [W]
        dict_payload[FREQUENCY_KEY] = data[7] / 10.0 # [Hz]
        print("<PAYLOAD>")
        print(json.dumps(dict_payload, indent=2))
        print("</PAYLOAD>")
      except modbus.ModbusInvalidResponseError as e:
        print("ModBus response error:")
        print(e)
      
      gauge = GaugeMetricFamily(GAUGE_KEY_NAME, "Voltdemort, PZEM-004T exporter", labels=['instance', 'measure'])
      for key,item in dict_payload.items():
        gauge.add_metric([TTY, key], item)
      yield gauge

if __name__ == "__main__":
  serial_device = "/dev/{}".format(TTY)

  killer = GracefulKiller()
  while not killer.kill_now:
    if not os.path.exists(serial_device):
      print('Waiting for device {} to appear...'.format(serial_device))
      time.sleep(2)
    else:
      break
  if killer.kill_now:
    sys.exit(0)

  try:
    # Connect to the slave
    serial = serial_interface.Serial(
      port=serial_device,
      baudrate=9600,
      bytesize=8,
      parity='N',
      stopbits=1,
      xonxoff=0
    )
  except Exception as e:
    print("Got exception opening serial port {}:".format(serial_device))
    print("An exception of type {0} occurred. Arguments:\n{1!r}".format(type(e).__name__, e.args))
    print("Exiting.")
    sys.exit(1)

  if not serial:
    print("Unable to get serial port {} - Unknown error.".format(serial_device))
    sys.exit(1)

  try:
    # Initialize modbus
    bus = modbus_rtu.RtuMaster(serial)
    bus.set_timeout(2.0)
    bus.set_verbose(True)
    # Start http server
    start_http_server(HTTP_PORT)
    # Disable default metrics
    REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
    REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
    REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)
    # Register voltdemort collector handler
    REGISTRY.register(VoltdemortCollector())
    print("Server listening on port {}".format(HTTP_PORT))
    # loop
    while not killer.kill_now:
      time.sleep(SLEEPER)
  except KeyboardInterrupt:
    print('exiting script')
  except Exception as e:
    print("Got exception:")
    print("An exception of type {0} occurred. Arguments:\n{1!r}".format(type(e).__name__, e.args))
  finally:
    bus.close()
