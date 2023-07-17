#!/usr/bin/python3

import time
import json
import os
import serial as serial_interface
import signal
import sys
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu
from modbus_tk import modbus

serial_device="/dev/ttyUSB0"

class GracefulKiller:
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self, *args):
    self.kill_now = True

if __name__ == "__main__":
  killer = GracefulKiller()
  while not killer.kill_now:
    if not os.path.exists(serial_device):
      print('Waiting for device {} to appear...'.format(serial_device))
      time.sleep(2)
    else:
      break
  if killer.kill_now:
    sys.exit(0)
  
  serial = None

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
    master = modbus_rtu.RtuMaster(serial)
    master.set_timeout(2.0)
    master.set_verbose(True)
    # Changing power alarm value to 100 W
    # master.execute(1, cst.WRITE_SINGLE_REGISTER, 1, output_value=100)
    while not killer.kill_now:
      dict_payload = {}
      try:
        data = master.execute(1, cst.READ_INPUT_REGISTERS, 0, 10)
        dict_payload["voltage"]= data[0] / 10.0
        dict_payload["current_A"] = (data[1] + (data[2] << 16)) / 1000.0 # [A]
        dict_payload["power_W"] = (data[3] + (data[4] << 16)) / 10.0 # [W]
        dict_payload["energy_Wh"] = data[5] + (data[6] << 16) # [Wh]
        dict_payload["frequency_Hz"] = data[7] / 10.0 # [Hz]
        dict_payload["power_factor"] = data[8] / 100.0
        dict_payload["alarm"] = data[9] # 0 = no alarm
        print("---- Payload ----")
        print(json.dumps(dict_payload, indent=2))
        print("---- /////// ----")
      except modbus.ModbusInvalidResponseError as e:
        print("ModBus response error:")
        print(e)
      time.sleep(10)
  except KeyboardInterrupt:
    print('exiting script')
  except Exception as e:
    print("Got exception:")
    print("An exception of type {0} occurred. Arguments:\n{1!r}".format(type(e).__name__, e.args))
  finally:
    master.close()
