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

import gtk
import gobject

class PopUp:
    '''
    Placeholder until I add libnotify support
    '''

    TIMEOUT = 4000          # ms

    def __init__(self, text):

        self.window = gtk.Window(type=gtk.WINDOW_POPUP)
        self.window.set_border_width(10)

        self.label = gtk.Label(text)

        frame = gtk.Frame()
        frame.set_label('SSH Key Applet')
        frame.add(self.label)
        frame.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        self.window.add(frame)

        self.window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.window.show_all()

        gobject.timeout_add(self.TIMEOUT, self.close_balloon)

    def close_balloon(self):
        self.window.hide_all()
        del self.label
        del self.window

if __name__ == '__main__':
    popup = PopUp('Fooo')
    gtk.main()

