#!/usr/bin/env python3

import sys
import os
import time
import logging
import subprocess
import shutil
import time
import threading
import mysql.connector
import socket

from datetime import datetime
from bluepy.btle import BTLEDisconnectError
from bluepy.btle import BTLEException
from miband import miband
from mysql.connector import connection
from mysql.connector import errorcode

FORMAT = '%(asctime)-15s %(name)s (%(levelname)s) > %(message)s'
#logging.basicConfig(filename='/var/log/hrm.log', format=FORMAT)
logging.basicConfig(format=FORMAT)
fileLog = logging.FileHandler('/var/log/hrm.log')
_log = logging.getLogger()
_log.setLevel(logging.DEBUG)
_log.addHandler(fileLog)


class MiConfig:
    def __init__(self, seconds, mac, key):
        self.seconds = seconds
        self.mac = mac
        self.key = bytes.fromhex(key)


class MiDb:
    def __init__(self):
        self.last_restart = 0
        self.insert_query = "INSERT INTO hr_log (mac, hr, record_timestamp) VALUES	(%s, %s,NOW());"
        self.cnx = None
        self.connect()

    def connect(self):
        try:
            self.cnx = connection.MySQLConnection(user='securecor', password='c3eBt9!nHQ',
                                                  host='localhost',
                                                  database='securecor')
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                _log.error(
                    "Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                _log.error("Database does not exist")
            else:
                _log.error(err)
        else:
            _log.debug("Connection to SQL susccessful")

    def log(self, mac, data):
        if (self.cnx == None):
            self.connect()
        sql_cursor = self.cnx.cursor()
        sql_cursor.execute(self.insert_query, (mac, data))
        self.cnx.commit()
        sql_cursor.close()

    def log_connect(self, mac):
        if (self.cnx == None):
            self.connect()
        sql_cursor = self.cnx.cursor()
        sql_cursor.execute(
            "INSERT INTO events (mac, event, record_timestamp) VALUES	(%s, 'CONNECT',NOW());", (mac))
        self.cnx.commit()
        sql_cursor.close()

    def log_disconnect(self, mac,reason):
        if (self.cnx == None):
            self.connect()
        sql_cursor = self.cnx.cursor()
        sql_cursor.execute(
            "INSERT INTO events (mac, event, message, record_timestamp) VALUES	(%s, 'DISCONNECT', %s, NOW());", (mac, reason))
        self.cnx.commit()
        sql_cursor.close()


db = MiDb()
configs = []
configs.append(MiConfig(30, "C0:63:64:53:34:E2",
               "0bf5d9aaf4e2413eb191dbd3fcb1ea2f"))
configs.append(MiConfig(30, "F6:81:78:7B:4F:2C",
               "e987f3ce65e443cbbb1a89b688e92699"))
maxAllowedHr = 100
alarms_server_ip = '193.176.229.2'
alarms_server_port = 5201
abonado = 2323
area = 1
zone = 1
event_line = 0
bt_initialized=False


def check_bt_restart():
    if ((time.monotonic()-db.last_restart) > 30):
        _log.error(
            "************************ Restarting Bluetooth ************************")
        db.last_restart = time.monotonic()
        os.system("sudo service bluetooth stop")
        os.system("sudo service bluetooth start")
        os.system("sudo systemctl stop bluetooth")
        os.system("sudo systemctl start bluetooth")
        _log.error(
            "************************ Waiting {} seconds ************************".format(config.seconds))
        time.sleep(config.seconds)


def signal(event, area, zone):
    global event_line
    event_line += 1
    now = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    signal_template = '\x02<?xml ver_sion="1.0"?><Packet ID="%d" Line="%d"><Signal EvType="SYS" Event="%s"><Area>%d</Area><Zone>%d</Zone><Date>%s</Date></Signal></Packet>\x03' % (
        abonado, event_line, event, area, zone, now)
    _log.debug('Sending {}'.format(signal_template))
    return signal_template


def send_alarm(mac, data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_address = (alarms_server_ip, alarms_server_port)
    print('connecting to {} port {}'.format(*server_address))
    sock.connect(server_address)

    try:
        event = 'HR({})={}'.format(mac, data)
        sock.sendall(bytes(signal(event, area, zone), encoding="raw_unicode_escape"))
        _log.debug('Event={}, Area={}, Zone={}'.format(event, area, zone))

    finally:
        print('closing socket')
        sock.close()


def heart_logger(band, data):
    _log.debug('{} Realtime heart BPM: {}'.format(band.mac_address, data))
    db.log(band.mac_address, data)
    if ((data > maxAllowedHr) and (time.monotonic()-band.last_alarm >= 120)):
        send_alarm(band.mac_address, data)
        band.last_alarm = time.monotonic()


def main_process(config):
    while True:
        try:
            _log.debug('Initializing {}'.format(config.mac))
            band = miband(config.mac, config.key, debug=True)
            band.initialize()
            now = datetime.now()
            print('Set time to:', now)
            band.set_current_time(now)
            db.log_connect(band.mac_address)
            global bt_initialized
            bt_initialized = True
            band.start_heart_rate_realtime(heart_measure_callback=heart_logger)
        except BTLEDisconnectError as e:
            try:
                db.log_disconnect(band.mac, e)
                _log.error("Disconnected from band {}".format(band.mac))
            except Exception:
                _log.error("Can't connect to band {}".format(config.mac))
        except BTLEException as e:
            _log.error(
                "************************ Exception ************************")
            _log.error(sys.exc_info())
            check_bt_restart()


if __name__ == "__main__":
    for config in configs:
        x = threading.Thread(target=main_process, args=(config,))
        x.start()
