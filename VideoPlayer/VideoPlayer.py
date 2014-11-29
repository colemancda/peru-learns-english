#!/usr/bin/env python
# -*- coding: utf-8 -*-

#   VideoPlayer.py por:
#   Flavio Danesse <fdanesse@gmail.com>
#   Uruguay

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import threading

from PlayerControls import PlayerControls
from ProgressPlayer import ProgressPlayer
from JAMediaReproductor.JAMediaReproductor import JAMediaReproductor

from Globales import COLORES


class VideoPlayer(gtk.EventBox):

    def __init__(self):

        gtk.EventBox.__init__(self)

        self.modify_bg(gtk.STATE_NORMAL, COLORES["text"])

        self.player = False
        self.video_path = ""

        vbox = gtk.VBox()
        self.visor = Visor()
        self.progress = ProgressPlayer()
        self.control = PlayerControls()

        vbox.pack_start(self.visor, True, True, 0)
        vbox.pack_start(self.progress, False, True, 0)
        vbox.pack_start(self.control, False, True, 0)

        self.add(vbox)
        self.show_all()

        self.control.connect("accion-controls", self.__control)
        self.progress.connect("seek", self.__seek)
        self.progress.connect("volumen", self.__volumen)

    def __endfile(self, widget=None, senial=None):
        if self.video_path:
            self.load(self.video_path)
        self.__control(False, "stop")

    def __update_progress(self, objetoemisor, valor):
        self.progress.set_progress(float(valor))

    def __state_changed(self, widget=None, valor=None):
        if "playing" in valor:
            self.control.set_playing()
        elif "paused" in valor or "None" in valor:
            self.control.set_paused()
        else:
            print "Estado del Reproductor desconocido:", valor

    def __seek(self, widget, valor):
        if self.player:
            self.player.set_position(valor)

    def __volumen(self, widget, valor):
        if self.player:
            self.player.set_volumen(valor)

    def __control(self, widget, accion):
        if accion == "stop":
            if self.player:
                self.player.stop()
        elif accion == "pausa-play":
            if self.player:
                self.player.pause_play()

    def load(self, path):
        self.video_path = path
        volumen = 1.0
        if self.player:
            volumen = float("{:.1f}".format(
                self.progress.volumen.get_value() * 10))
            self.player.disconnect_by_func(self.__endfile)
            self.player.disconnect_by_func(self.__state_changed)
            self.player.disconnect_by_func(self.__update_progress)
            self.player.stop()
            del(self.player)
            self.player = False

        xid = self.visor.get_property('window').xid
        self.player = JAMediaReproductor(xid)

        self.player.connect("endfile", self.__endfile)
        self.player.connect("estado", self.__state_changed)
        self.player.connect("newposicion", self.__update_progress)

        self.player.load(path)
        self._thread = threading.Thread(target=self.player.play)
        self._thread.start()
        self.player.set_volumen(volumen)
        self.progress.volumen.set_value(volumen / 10)

    def stop(self):
        self.__control(False, "stop")


class Visor(gtk.DrawingArea):

    def __init__(self):

        gtk.DrawingArea.__init__(self)

        self.modify_bg(gtk.STATE_NORMAL, COLORES["text"])

        self.show_all()