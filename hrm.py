#!/usr/bin/env python3

import subprocess
import shutil
import time
import threading

from datetime import datetime
from bluepy.btle import BTLEDisconnectError
from miband import miband


class MiConfig:
  def __init__(self, mac, key):
    self.mac = mac
    self.key = bytes.fromhex(key)

configs = []
configs.append(MiConfig("C0:63:64:53:34:E2","0bf5d9aaf4e2413eb191dbd3fcb1ea2f"))
configs.append(MiConfig("F6:81:78:7B:4F:2C","e987f3ce65e443cbbb1a89b688e92699"))

def heart_logger(band, data):
    print (band.mac_address, 'Realtime heart BPM:', data)

def doit(config):
  print (config.mac, config.key.hex())
  band=miband(config.mac, config.key, debug=True)
  band.initialize()
  band.start_heart_rate_realtime(heart_measure_callback=heart_logger)

if __name__ == "__main__":
    for config in configs:
      x = threading.Thread(target=doit, args=(config,))
      x.start()

