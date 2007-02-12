#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Copyright 2007 Menno Smits
# Written by Menno Smits <menno _at_ freshfoo.com>

import dbus
import dbus.glib
from sets import Set

class VolumeWatcher:

    '''
    Listens for DBUS signals from HAL and calls a callback function when a
    volume is mounted.

    The callback should take a single 'mount point' argument. 
    If the callback returns True then the volume will be unmounted when the 
    callback returns.
    '''

    def __init__(self, callback):
        self.callback = callback
        self.bus = dbus.SystemBus()
        hal_manager_obj = self.bus.get_object('org.freedesktop.Hal', 
                                         '/org/freedesktop/Hal/Manager')
        self.hal_manager = dbus.Interface(hal_manager_obj,
                                     'org.freedesktop.Hal.Manager')

        self.hal_manager.connect_to_signal('DeviceAdded', self.device_added)

    def device_added(self, udi):

        # Only care about new volumes, not other devices. 
        # Filter by the UDI path rather than creating a proxy object and
        # checking for volumes because it's more efficient this way.
        if not udi.startswith('/org/freedesktop/Hal/devices/volume_'):
            return

        volume = self.bus.get_object("org.freedesktop.Hal", udi)

        # Wait for property changes
        self.bus.add_signal_receiver(
                lambda *args: self.property_modified(volume, *args),
                'PropertyModified',
                "org.freedesktop.Hal.Device", "org.freedesktop.Hal", 
                udi)
                
    def property_modified(self, volume, num_changes, changes):
        for name, removed, added in changes:
            if name == 'volume.is_mounted' and volume.GetProperty(name):
                # Don't care about property changes from this volume anymore
                self.bus.remove_signal_receiver(
                        None, 
                        'PropertyModified',
                        "org.freedesktop.Hal.Device", "org.freedesktop.Hal", 
                        volume.GetProperty(u'info.udi')) 
                
                # Volume is mounted, call handler
                self.volume_mounted(volume)
        
    def volume_mounted(self, volume):
        mount_point = volume.GetProperty(u'volume.mount_point')

        if self.callback(mount_point):
            # callback indicated that unmount should be done
            volume_manager = dbus.Interface(volume, 
                'org.freedesktop.Hal.Device.Volume')
            volume_manager.Unmount(['lazy'])

