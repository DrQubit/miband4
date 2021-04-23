#!/usr/bin/env python3

import subprocess
import shutil
import time
from datetime import datetime

from bluepy.btle import BTLEDisconnectError

from miband import miband


class MiConfig:
  mac = ""
  key = ""

AUTH_KEY = bytes.fromhex(AUTH_KEY)
