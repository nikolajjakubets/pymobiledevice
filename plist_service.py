#
# pymobiledevice - Jython implementation of libimobiledevice
#
# Copyright (C) 2014  Taconut <https://github.com/Triforce1>
# Copyright (C) 2014  PythEch <https://github.com/PythEch>
# Copyright (C) 2013  GotoHack <https://github.com/GotoHack>
#
# pymobiledevice is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pymobiledevice is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pymobiledevice.  If not, see <http://www.gnu.org/licenses/>.

import os
import plistlib
import struct
from re import sub
from usbmux import usbmux
from util.bplist import BPlistReader


class PlistService(object):
    def __init__(self, port, udid=None):
        self.port = port
        self.connect(udid)

    def connect(self, udid=None):
        mux = usbmux.USBMux()
        mux.process(5.0)
        dev = None

        while not dev and mux.devices:
            if udid:
                for d in mux.devices:
                    if d.serial == udid:
                        dev = d
                        print "Connecting to device: " + dev.serial
            else:
                dev = mux.devices[0]
                print "Connecting to device: " + dev.serial

        try:
            self.socket = mux.connect(dev, self.port)
        except:
            raise Exception("Connection to device port %d failed" % self.port)
        return dev.serial

    def close(self):
        self.socket.close()

    def recv(self, len=4096):
        return self.socket.recv(len)

    def send(self, data):
        return self.socket.send(data)

    def recv_exact(self, l):
        data = ""
        while l > 0:
            d = self.recv(l)
            if not d or len(d) == 0:
                break
            data += d
            l -= len(d)
        return data

    def recv_raw(self):
        l = self.recv(4)
        if not l or len(l) != 4:
            return
        l = struct.unpack(">L", l)[0]
        return self.recv_exact(l)

    def send_raw(self, data):
        return self.send(struct.pack(">L", len(data)) + data)

    def recvPlist(self):
        payload = self.recv_raw()
        #print '<<<<<<<<',payload
        if not payload:
            return
        if payload.startswith("bplist00"):
            return BPlistReader(payload).parse()
        elif payload.startswith("<?xml"):
            #HAX lockdown HardwarePlatform with null bytes
            payload = sub('[^\w<>\/ \-_0-9\"\'\\=\.\?\!\+]+', '', payload.decode('utf-8')).encode('utf-8')
            return plistlib.readPlistFromString(payload)
        else:
            raise Exception("recvPlist invalid data : %s" % payload[:100].encode("hex"))

    def sendPlist(self, d):
        payload = plistlib.writePlistToString(d)
        #print '>>>>',payload
        l = struct.pack(">L", len(payload))
        self.send(l + payload)

    def sendRequest(self, plist):
        self.sendPlist(plist)
        return self.recvPlist()

    def start_ssl(self, keyfile):
        if os._name == 'nt':
            self.socket = usbmux.SSLSocket(self.socket.sock._sock._get_jsocket(), keyfile)
        else:
            self.socket = usbmux.SSLSocket(self.socket.sock, keyfile)
