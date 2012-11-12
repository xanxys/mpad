#!/bin/env python
"""
/usr/share/applications/xanxys.desktop is needed to launch from gnome menu or nautilus "open with" dialog.

Description of .desktop file: http://developer.gnome.org/integration-guide/stable/desktop-files.html.en

"""
import pygtk
pygtk.require('2.0')
import gtk

class Base:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.show()

    def main(self):
        gtk.main()


if __name__ == "__main__":
    base = Base()
    base.main()
