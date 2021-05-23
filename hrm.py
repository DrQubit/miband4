#!/usr/bin/env python3

import sys,os,time
import logging
import subprocess
import shutil
import time
import threading
import mysql.connector
import socket

from datetime import datetime
from bluepy.btle import BTLEDisconnectError
from miband import miband
from mysql.connector import connection
from mysql.connector import errorcode

FORMAT = '%(asctime)-15s %(name)s (%(levelname)s) > %(message)s'
#logging.basicConfig(filename='/var/log/hrm.log', format=FORMAT)
logging.basicConfig(format=FORMAT)
_log = logging.getLogger()
_log.setLevel(logging.DEBUG)


class MiConfig:
  def __init__(self, seconds, mac, key):
    self.seconds = seconds
    self.mac = mac
    self.key = bytes.fromhex(key)


class MiDb:
  def __init__(self):
    self.last_restart = 0
    self.insert_query = "INSERT INTO hr (mac, hr, record_timestamp) VALUES	(%s, %s,NOW());"
    self.cnx = None
    self.connect()

  def connect(self):
    try:
      self.cnx = connection.MySQLConnection(user='sql11407604', password='eEyKVLq6HM',
                                    host='sql11.freesqldatabase.com',
                                    database='sql11407604')
    except mysql.connector.Error as err:
      if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        _log.error("Something is wrong with your user name or password")
      elif err.errno == errorcode.ER_BAD_DB_ERROR:
        _log.error("Database does not exist")
      else:
        _log.error(err)
    else:
      _log.debug("Connection to SQL susccessful")

  def log (self, mac, data):
    if (self.cnx==None):
      self.connect()
    sql_cursor = self.cnx.cursor()
    sql_cursor.execute(self.insert_query, (mac, data))
    self.cnx.commit()
    sql_cursor.close()

db = MiDb()
configs = []
configs.append(MiConfig(30,"C0:63:64:53:34:E2","0bf5d9aaf4e2413eb191dbd3fcb1ea2f"))
configs.append(MiConfig(30,"F6:81:78:7B:4F:2C","e987f3ce65e443cbbb1a89b688e92699"))
maxAllowedHr=100
alarms_server_ip='193.176.229.2'
alarms_server_port=5201
abonado = 2323
event = "*A"
area = 1
zone = 1
event_line = 0
 
def check_bt_restart():
  if ((time.clock_gettime(time.CLOCK_MONOTONIC)-db.last_restart) > 30):
      _log.error(
          "************************ Restarting Bluetooth ************************")
      db.last_restart = time.clock_gettime(time.CLOCK_MONOTONIC)
      os.system("sudo service bluetooth stop")
      os.system("sudo service bluetooth start")
      os.system("sudo systemctl stop bluetooth")
      os.system("sudo systemctl start bluetooth")
      _log.error(
          "************************ Waiting {} seconds ************************".format(config.seconds))
      time.sleep(config.seconds)


def signal (event, area, zone):
  global event_line
  event_line+=1
  now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
  signal_template = '\x02<?xml ver_sion="1.0"?><Packet ID="%d" Line="%d"><Signal EvType="SYS" Event="%s"><Area>%d</Area><Zone>%d</Zone><Date>%s</Date></Signal></Packet>\x03' % (abonado, event_line, event,area,zone,now)
  _log.debug('Sending {}'.format(signal_template))
  return signal_template

def send_alarm():
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  server_address = (alarms_server_ip, alarms_server_port)
  print('connecting to {} port {}'.format(*server_address))
  sock.connect(server_address)

  try:
      sock.sendall(bytes(signal(event, area, zone), encoding="raw_unicode_escape"))

  finally:
      print('closing socket')
      sock.close()


def heart_logger(band, data):
    _log.debug('{} Realtime heart BPM: {}'.format(band.mac_address, data))
    db.log(band.mac_address, data)
    if data > maxAllowedHr:
      send_alarm()


def main_process(config):
  while True:
    try:
      _log.debug('Initializing {}'.format(config.mac))
      band=miband(config.mac, config.key, debug=True)
      band.initialize()
      now = datetime.now()
      print ('Set time to:', now)
      band.set_current_time(now)
      band.start_heart_rate_realtime(heart_measure_callback=heart_logger)
    except:
      _log.error ("************************ Exception ************************")
      _log.error (sys.exc_info())
      check_bt_restart()


if __name__ == "__main__":
  for config in configs:
    x = threading.Thread(target=main_process, args=(config,))
    x.start()
