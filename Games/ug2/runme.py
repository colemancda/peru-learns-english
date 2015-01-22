
#!/bin/env python2
# -*- coding: utf-8 -*-

#   Juego UG2 por:
#   Sebastian Silva <sebastian@fuentelibre.org>
#   Planeta Tierra

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
import sys
import os

game_dir = os.path.abspath(os.path.dirname(__file__))
def gamedir(archivo):
    return os.path.join(game_dir, archivo)

sys.path.insert(1, gamedir("../../Lib/"))

import pygame
import spyral
import random
import csv
import collections
pygame.mixer.init()

SIZE = (700, 700)
TILE = (64, 64)

def play(res):
    if not Escena.MUTE:
        res.play()

def wrap(text, length):
    """
    Sirve para cortar texto en varias lineas
    """
    words = text.split()
    lines = []
    line = ''
    for w in words:
        if len(w) + len(line) > length:
            lines.append(line)
            line = ''
        line = line + w + ' '
        if w is words[-1]:
            lines.append(line)
    return '\n'.join(lines)


font_path = gamedir("../fonts/DejaVuSans.ttf")
topic_dir = gamedir("../../Topics/Topic_4/")


def obtener_palabra(topic_dir):
    archivo = os.path.join(topic_dir, "vocabulario.csv")
    tabla = csv.DictReader(file(archivo))
    lista = []
    for linea in tabla:
        uid = linea["id"]
        palabra_png = os.path.join(topic_dir, "Imagenes", uid + '.png')
        #if os.path.exists(palabra_png):
        lista.append(linea)

    indice = random.randint(0, len(lista) - 1)

    palabra = lista[indice]["term"]
    uid = lista[indice]["id"]
    palabra_png = os.path.join(topic_dir, "Imagenes", uid + '.png')

    return palabra, palabra_png

def obtener_set(topic):
    conjunto = list()
    while len(conjunto)<5:
        nueva = obtener_palabra(topic)
        if nueva not in conjunto:
            conjunto.append(nueva)
    return conjunto

class Tablero(spyral.View):
    def __init__(self, scene, topic, mapa):
        spyral.View.__init__(self, scene)

        margin = (700 - (140 * 5)) / 2

        self.pos = (margin, margin)
        self.layers = ["abajo", "arriba", "primer"]

        self.cursor = Cursor(self)

        self.tablero = mapa

        self.palabras = obtener_set(topic)
        self.topic = topic

        self.camino = []
        self.ACTIVADO = False
        self.mov_anterior = None
        self.intentos = 0

        for row in range(len(self.tablero)):
            for col in range(len(self.tablero[row])):
                tablero = self.tablero[row][col]
                if tablero:
                    palabra = self.palabras[tablero-1][0]
                    archivo = self.palabras[tablero-1][1]
                    bloque = Bloque(self, row, col, COLOR=tablero-1,
                                    PALABRA=palabra, ARCHIVO=archivo)
                    self.tablero[row][col] = bloque
                else:
                    nexo = Nexo(self, row, col)
                    self.tablero[row][col] = nexo

        spyral.event.register ("input.keyboard.down.tab", self.blinkall)
        spyral.event.register ("input.keyboard.down.escape", self.openall)

        spyral.event.register("input.mouse.motion", self.handle_motion)
        spyral.event.register("Tablero.activar", self.activar)
        spyral.event.register("Tablero.movimiento", self.movimiento)

        self.activar_snd = pygame.mixer.Sound(gamedir("sonidos/Retro_Game_Sounds_SFX_162.ogg"))
        self.match_snd = pygame.mixer.Sound(gamedir("sonidos/Powerup.wav"))
        self.desactivar_snd = pygame.mixer.Sound(gamedir("sonidos/Randomize2.wav"))
        self.win_snd = pygame.mixer.Sound(gamedir("sonidos/Retro_Game_Sounds_SFX_161.ogg"))

    def reset(self, mapa):
        self.palabras = obtener_set(self.topic)

        Bloque.RENDERED = None
        self.camino = []
        self.ACTIVADO = False
        self.mov_anterior = None
        self.intentos = 0

        nexos = []
        bloques = []
        for fila in self.tablero:
            for item in fila:
                if item.__class__.__name__=="Nexo":
                    item.reset()
                    nexos.append(item)
                else:
                    bloques.append(item)

        for row in range(len(mapa)):
            for col in range(len(mapa[row])):
                tablero = mapa[row][col]
                if tablero:
                    palabra = self.palabras[tablero-1][0]
                    archivo = self.palabras[tablero-1][1]
                    bloque = bloques.pop()
                    bloque.reset( row, col, COLOR=tablero-1,
                                    PALABRA=palabra, ARCHIVO=archivo)
                    bloque.iopen()
                    self.tablero[row][col] = bloque
                else:
                    nexo = nexos.pop()
                    nexo.reset(row, col)
                    self.tablero[row][col] = nexo


    def activar(self, ubicacion):
        if self.ACTIVADO:
            self.desactivar()
        self.ACTIVADO = ubicacion
        self.ACTIVADO_INICIAL = ubicacion
        #print "Activado: "+str(ubicacion)
        play(self.activar_snd)

    def desactivar(self, camino=None, unless=None):
        if not camino:
            camino = self.camino
        if camino:
            play(self.desactivar_snd)
        for ubicacion in camino:
            nexo = self.tablero[ubicacion.y][ubicacion.x]
            nexo.reset()
        self.camino = []
        event = spyral.event.Event(unless=unless)
        spyral.event.queue("Bloque.open", event)
        self.ACTIVADO = False

    def match(self, primero, segundo):
        self.ACTIVADO = False
        primero.match(self.camino)
        segundo.match(self.camino)
        self.camino = []
        self.check_win()
        play(self.match_snd)

    def check_win(self):
        bloques_rest = 0
        nexos_rest = 0
        for fila in self.tablero:
            for bloque in fila:
                if "Bloque" in bloque.__class__.__name__:
                    if not bloque.MATCH:
                        bloques_rest += 1
                elif "Nexo" in bloque.__class__.__name__:
                    if not bloque.visible:
                        nexos_rest += 1
        if bloques_rest==0 and nexos_rest>0:
            # Avisar al usuario que debe llenar la pantalla
            self.win()
        elif bloques_rest==0 and nexos_rest==0:
            self.win()

    def win(self):
        Bloque.RENDERED = []
        spyral.event.queue("Bloque.final")
        spyral.event.queue("Tablero.score")
        play(self.win_snd)

    def get_match(self, primero):
        for fila in self.tablero:
            for bloque in fila:
                if "Bloque" in bloque.__class__.__name__:
                    if bloque.COLOR==primero.COLOR and bloque is not primero:
                        return bloque


    def movimiento(self, ubicacion):
        #print "Movimiento: "+str(ubicacion)
        self.scene.tablero.cursor.ubicacion = spyral.Vec2D(ubicacion)

        if self.ACTIVADO:
            if (ubicacion.distance(self.ACTIVADO))==1.0:
                ANTERIOR = self.tablero[self.ACTIVADO.y][self.ACTIVADO.x]
                try:
                    CANDIDATO = self.tablero[ubicacion.y][ubicacion.x]
                except IndexError:
                    self.intentos += 1
                    self.desactivar()
                    return
                if "Nexo" in CANDIDATO.__class__.__name__:
                    if CANDIDATO.visible:
                        return
                    if "Nexo" in ANTERIOR.__class__.__name__:
                        ANTERIOR.ir_a(ubicacion)
                    # Encontramos el camino!
                    CANDIDATO.venir_de(self.ACTIVADO)
                    self.ACTIVADO = ubicacion
                    self.camino.append(ubicacion)
                else:
                    self.intentos += 1
                    if "Nexo" in ANTERIOR.__class__.__name__:
                        ANTERIOR.ir_a(ubicacion)
                    INICIAL = self.tablero[self.ACTIVADO_INICIAL.y][self.ACTIVADO_INICIAL.x]
                    if CANDIDATO.COLOR==INICIAL.COLOR and (CANDIDATO is not INICIAL):
                        self.match(INICIAL, CANDIDATO)
                    elif CANDIDATO==INICIAL:
                        return
                    else:
                        self.desactivar()

    def handle_motion(self, pos):
        self.scene.tablero.cursor.pos = pos
        if self.ACTIVADO:
            from_pos = (pos - self.scene.tablero.pos) / spyral.Vec2D(140,140)
            ubicacion = spyral.Vec2D(int(from_pos.x), int(from_pos.y))
            if ubicacion!=self.mov_anterior and ubicacion!=self.ACTIVADO:
                self.mov_anterior=ubicacion
                event = spyral.event.Event(ubicacion=ubicacion)
                spyral.event.queue("Tablero.movimiento", event)

    def blinkall(self):
        spyral.event.queue("Bloque.blink")

    def openall(self):
        spyral.event.queue("Bloque.open")

    #def update(self):
    #    for line in self.estado:
    #        self.

class Nexo (spyral.Sprite):
    def __init__(self, scene, row, col):
        spyral.Sprite.__init__(self, scene)

        self.layer = "abajo"

        self.vengo_de = None

        self.gonorth = spyral.Image(filename=gamedir("imagenes/go-north.png"))
        self.gosouth = spyral.Image(filename=gamedir("imagenes/go-south.png"))
        self.gowest = spyral.Image(filename=gamedir("imagenes/go-west.png"))
        self.goeast = spyral.Image(filename=gamedir("imagenes/go-east.png"))

        spyral.event.register ("Cursor.click", self.check_click)

        self.pos = spyral.Vec2D(col * 135, row * 135)
        self.pos = (col * 140 + 70, row * 140 + 70)
        self.anchor = "center"

        self.ROW = row
        self.COL = col

        self.visible = False

    def reset(self, row=None, col=None):
        if row is not None and col is not None:
            self.pos = (col * 140 + 70, row * 140 + 70)
            self.ROW = row
            self.COL = col
        self.vengo_de = None
        self.visible = False

    def ir_a(self, ubicacion):
        direccion = spyral.Vec2D(self.COL, self.ROW) - ubicacion

        name = "canopy_"

        if self.vengo_de==(0,1):
            name += "north"
        if self.vengo_de==(0,-1):
            name += "south"
        if self.vengo_de==(-1,0):
            name += "east"
        if self.vengo_de==(1,0):
            name += "west"

        name += "_"

        if direccion==(0,1):
            name += "north"
        if direccion==(0,-1):
            name += "south"
        if direccion==(-1,0):
            name += "east"
        if direccion==(1,0):
            name += "west"

        name += ".png"

        try:
            self.image = spyral.Image(filename=gamedir("imagenes/"+name))
        except pygame.error:
            pass

    def venir_de(self, ubicacion):
        self.visible = True

        direccion = tuple(spyral.Vec2D(self.COL, self.ROW) - ubicacion)

        if not self.vengo_de:
            self.vengo_de = spyral.Vec2D(direccion)
            if direccion == (0, +1):
                self.image = self.gosouth
            elif direccion == (0, -1):
                self.image = self.gonorth
            elif direccion == (-1, 0):
                self.image = self.gowest
            elif direccion == (+1, 0):
                self.image = self.goeast

    def check_click(self, pos):
        if self.collide_point(pos):
            self.scene.tablero.cursor.pos = pos
            event = spyral.event.Event(ubicacion=spyral.Vec2D(self.COL, self.ROW))
            spyral.event.queue("Tablero.movimiento", event)

    def check_pos(self, pos):
        r = spyral.Rect(self.pos.x + 20, self.pos.y + 20, self.pos.x+100, self.pos.y+100)
        if r.collide_point(pos):
            event = spyral.event.Event(ubicacion=spyral.Vec2D(self.ROW, self.COL))
            spyral.event.queue("Tablero.movimiento", event)


class Cursor (spyral.Sprite):
    def __init__(self, scene):
        spyral.Sprite.__init__(self, scene)

        self.ubicacion = spyral.Vec2D(2, 2)

        self.anchor = "center"
        self.layer = "primer"
        self.image = spyral.Image(filename=gamedir("imagenes/square-01-whole.png"))
        self.scale = 0.5

        spyral.event.register ("input.keyboard.down.left", self.left)
        spyral.event.register ("input.keyboard.down.up", self.up)
        spyral.event.register ("input.keyboard.down.down", self.down)
        spyral.event.register ("input.keyboard.down.right", self.right)

        spyral.event.register("input.keyboard.down.keypad_2", self.down)
        spyral.event.register("input.keyboard.down.keypad_8", self.up)
        spyral.event.register("input.keyboard.down.keypad_4", self.left)
        spyral.event.register("input.keyboard.down.keypad_6", self.right)

        spyral.event.register("input.keyboard.down.keypad_3", self.click)
        spyral.event.register("input.keyboard.down.keypad_9", self.click)
        spyral.event.register("input.keyboard.down.keypad_7", self.click)
        spyral.event.register("input.keyboard.down.keypad_1", self.click)

        spyral.event.register ("input.keyboard.down.space", self.click)
        spyral.event.register ("input.keyboard.down.return", self.click)

        self.desplaz_anim = None

        self.update()

    def click(self):
        event = spyral.event.Event(pos=self.pos)
        spyral.event.queue("Cursor.click", event)

    def left(self):
        self.ubicacion = spyral.Vec2D((self.ubicacion.x - 1) % 5 , self.ubicacion.y)
        self.update()

    def right(self):
        self.ubicacion = spyral.Vec2D((self.ubicacion.x + 1) % 5, self.ubicacion.y)
        self.update()

    def down(self):
        self.ubicacion = spyral.Vec2D(self.ubicacion.x, (self.ubicacion.y + 1) % 5)
        self.update()

    def up(self):
        self.ubicacion = spyral.Vec2D(self.ubicacion.x, (self.ubicacion.y - 1) % 5)
        self.update()

    def update(self):
        newpos = self.ubicacion * spyral.Vec2D(140, 140) + spyral.Vec2D(70, 70)

        if self.desplaz_anim:
            self.stop_animation(self.desplaz_anim)

        self.desplaz_anim = spyral.Animation("pos", QuadraticOutTuple(self.pos, newpos),
                                                duration=0.4)
        self.animate(self.desplaz_anim)

        event = spyral.event.Event(ubicacion=self.ubicacion)
        spyral.event.queue("Tablero.movimiento", event)

class Bloque (spyral.Sprite):
    # RENDERED lleva la cuenta para todos los bloques,
    #          de que palabras ya salieron en pantalla.
    RENDERED = None

    def __init__(self, scene, row, col, COLOR=4, PALABRA="error", ARCHIVO=None):
        # spritesheet color: yellow, green, orange, blue, brown
        spyral.Sprite.__init__(self, scene)
        self.layer = "arriba"

        self.COLOR = COLOR
        self.BGCOLOR = 4

        self.ROW = row
        self.COL = col
        self.PALABRA = PALABRA
        self.ARCHIVO = ARCHIVO
        self.font = spyral.Font(font_path, 28, (0, 0, 0))
        self.line_height = self.font.linesize

        self.mode = "PALABRA"
        if Bloque.RENDERED and (PALABRA in Bloque.RENDERED):
            self.mode = "TARJETA"
        elif not Bloque.RENDERED:
            Bloque.RENDERED = [ PALABRA ]
        else:
            Bloque.RENDERED.append( PALABRA )

        # Somos un ojo del espacio
        assert COLOR != -1

        self.full_image = spyral.Image(
            filename=gamedir("imagenes/eye-tiles.png"))

        self.anchor = "center"
        self.pos = (col * 140 + 70, row * 140 + 70)
        self.ARMADO = 3
        self.CERRADO = 2
        self.CERRANDO = 1
        self.ABIERTO = 0

        self.abierto = True
        self.oculto = False

        self.init_animations()

        self.margin = 2
        self.marco = spyral.Image(filename=gamedir("imagenes/marco_1.png"))
        self.image = self.marco

        spyral.event.register("Bloque.blink", self.blink)
        spyral.event.register("Bloque.open", self.iopen)
        spyral.event.register("Bloque.final", self.final)

        spyral.event.register ("input.mouse.down.left", self.check_click)
        spyral.event.register ("Cursor.click", self.check_click)

        self.scale = 0.9
        self.showself()

        self.MATCH = False

    def __repr__(self):
        return "Bloque en (" + str(self.ROW) + "," + str(self.COL) + ")"

    def reset(self, row, col, COLOR=4, PALABRA="error", ARCHIVO=None):
        self.pos = (col * 140 + 70, row * 140 + 70)
        self.ROW = row
        self.COL = col

        self.COLOR = COLOR
        self.BGCOLOR = COLOR
        self.oculto = False

        self.mode = "PALABRA"
        if Bloque.RENDERED and (PALABRA in Bloque.RENDERED):
            self.mode = "TARJETA"
        elif not Bloque.RENDERED:
            Bloque.RENDERED = [ PALABRA ]
        else:
            Bloque.RENDERED.append( PALABRA )

        self.PALABRA = PALABRA
        self.ARCHIVO = ARCHIVO
        self.MATCH = False

        self.init_animations()

    def match(self, camino):
        self.oculto = True
        self.abierto = False
        self.BGCOLOR = self.COLOR
        self.MATCH = camino
        self.blink()

    def update(self):
        if self.oculto:
            if self.abierto:
                self.image = self.tiled(self.ABIERTO, self.BGCOLOR)
            else:
                self.image = self.tiled(self.ARMADO, self.BGCOLOR)
        else:
            self.showself()

    def render_text(self, text):
        ancho_promedio = self.font.get_size("X")[0]
        caracteres = (self.width - 2 * self.margin) / ancho_promedio
        lineas = wrap(text, caracteres).splitlines()

        altura = len(lineas) * self.line_height
        bloque = spyral.Image(size=(self.width, altura))

        ln = 0
        for linea in lineas:
            bloque.draw_image(image=self.font.render(linea),
                position=(0, ln * self.line_height), anchor="midtop")
            ln = ln + 1

        nueva = spyral.Image(size=(self.width - self.margin,
            self.height - self.margin)).fill((255, 255, 255))
        nueva.draw_image(bloque,
            position=(0, 0), anchor="midleft")

        return nueva

    def render_image(self, image):
        try:
            nueva = spyral.Image(filename=image).scale((
                self.width - self.margin, self.height - self.margin))
        except pygame.error:
            nueva = spyral.Image(size=(self.width - self.margin,
                self.height - self.margin)).fill((255, 255, 255))
        return nueva

    def showself(self):
        self.image = self.marco
        if self.mode == "TARJETA":
            self.image.draw_image(self.render_image(self.ARCHIVO),
                position=(0, 0), anchor="center")
        elif self.mode == "PALABRA":
            self.image.draw_image(self.render_text(self.PALABRA),
                position=(0, 0), anchor="center")

    def init_animations(self):
        # ABRIR
        secuencia = [self.tiled(self.ARMADO, self.COLOR)] + \
                    [self.tiled(self.CERRADO, self.COLOR)] * 6 + \
                    [self.tiled(self.CERRANDO, self.COLOR)] + \
                    [self.tiled(self.ABIERTO, self.COLOR)] * 6
        # Y CERRAR
        retro_secuencia = list(reversed(secuencia))
        toda_secuencia = secuencia + retro_secuencia

        self.open_animation = spyral.Animation("image", spyral.easing.Iterate(secuencia, times=0.9), 1)
        self.close_animation = spyral.Animation("image", spyral.easing.Iterate(retro_secuencia, times=0.9), 1)
        self.blink_animation = spyral.Animation("image", spyral.easing.Iterate(toda_secuencia), 2)

        spyral.event.register("Bloque.image.animation.end", self.update)


    def lado_mas_cercano(self):
        x = self.x
        y = self.y
        izq = spyral.Vec2D(0 - self.width/2, y)
        der = spyral.Vec2D(self.scene.width + self.width/2, y)
        arr = spyral.Vec2D(x, 0 - self.height/2)
        aba = spyral.Vec2D(x, self.scene.height + self.height/2)

        punto = spyral.Vec2D(x,y)

        mayor = self.scene.width
        for borde in [izq, der, aba, arr]:
            dist = punto.distance(borde)
            if dist < mayor:
                mayor = dist
                borde_mayor = borde

        return borde_mayor

    def tiled(self, x, COLOR=None):
        BIGTILE = (120, 120)
        if COLOR==None:
            COLOR = self.BGCOLOR
        return self.full_image.copy().crop((x * 132, COLOR * 132), BIGTILE)

    def check_click(self, pos):
        if self.collide_point(pos):
            if not self.MATCH:
                if self.abierto:
                    self.iclose()
                else:
                    self.iopen()
                    self.scene.tablero.desactivar()
                event = spyral.event.Event(ubicacion=spyral.Vec2D(self.COL, self.ROW))
                spyral.event.queue("Tablero.movimiento", event)
            else:
                self.scene.tablero.desactivar(self.MATCH, unless=self)
                alter = self.scene.tablero.get_match(self)
                self.MATCH = False
                alter.MATCH = False
                alter.iopen()
                self.scene.tablero.activar(spyral.Vec2D(self.COL, self.ROW))

    def check_pos(self, pos):
        if self.collide_point(pos):
            return self

    def final(self):
        self.abierto = True
        #self.blink()

        # ESCAPAR
        #self.escape_animation = spyral.Animation("pos", QuadraticOutTuple(self.pos, self.lado_mas_cercano()), 3)
        #try:
        #    self.animate (self.escape_animation)
        #except:
        #    pass

    def iopen(self, unless=None):
        if (not unless==self) and (not self.MATCH):
            self.oculto = False
            if not self.abierto:
                try:
                    self.animate (self.open_animation)
                    self.abierto = True
                except:
                    pass

    def iclose(self):
        event = spyral.event.Event(ubicacion=spyral.Vec2D(self.COL, self.ROW))
        spyral.event.queue("Tablero.activar", event)
        event = spyral.event.Event(unless=self)
        spyral.event.queue("Bloque.open", event)
        self.BGCOLOR = self.COLOR
        self.oculto = True
        if self.abierto:
            try:
                self.animate (self.close_animation)
                self.abierto = False
            except:
                pass

    def blink(self):
        try:
            self.animate (self.blink_animation)
        except:
            pass


class Escena(spyral.Scene):

    MUTE = False
    gameview = False
    n = 0

    def __init__(self, topic=topic_dir, gameview=False):

        spyral.Scene.__init__(self, SIZE)

        img = spyral.Image(filename=gamedir(
            "imagenes/Fazenda_Colorada.jpg")).scale(self.scene.size)

        #n = pygame.Surface.convert_alpha(img._surf)
        #n.fill((64, 0, 0, 127))
        #img._surf.blit(n, (0, 0))

        self.background = img

        self.mapas = []
        self.mapas.append(
            [[1, 0, 0, 0, 2],
            [3, 0, 0, 4, 0],
            [0, 1, 2, 5, 0],
            [0, 0, 3, 0, 0],
            [5, 0, 0, 0, 4]]
            )
        self.mapas.append(
            [[0, 0, 0, 1, 2],
            [0, 1, 3, 0, 0],
            [0, 0 ,0, 0, 0],
            [3, 4, 0, 0, 2],
            [5, 0, 5, 0, 4]]
            )
        self.mapas.append(
            [[0, 0, 0, 0, 1],
            [2, 3, 0, 2, 0],
            [0, 4, 0, 0, 0],
            [0, 3, 0, 1, 5],
            [0, 4, 5, 0, 0]]
            )
        self.mapas.append(
            [[1, 2, 3, 0, 3],
            [0, 0, 2, 4, 0],
            [0, 5, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [5, 0, 0, 0, 4]]
            )
        self.mapas.append(
            [[0, 0, 1, 2, 0],
            [0, 0, 3, 4, 0],
            [0, 0, 5, 0, 0],
            [1, 0, 0, 4, 0],
            [3, 0, 0, 5, 2]]
            )
        self.mapas.append(
            [[1, 0, 0, 0, 2],
            [0, 3, 2, 1, 0],
            [0, 4, 0, 0, 0],
            [0, 0, 5, 0, 0],
            [3, 0, 0, 4, 5]]
            )
        self.mapas.append([
            [1, 0, 2, 0, 0],
            [3, 0, 0, 1, 0],
            [0, 4, 2, 0, 0],
            [0, 0, 0, 0, 4],
            [0, 3, 5, 0, 5]]
            )
        self.mapas.append([
            [0, 0, 0, 0, 1],
            [0, 2, 3, 4, 0],
            [4, 0, 0, 1, 0],
            [2, 0, 0, 3, 5],
            [5, 0, 0, 0, 0]]
            )
        self.mapas.append([
            [0, 0, 0, 1, 2],
            [0, 3, 0, 0, 0],
            [0, 0, 0, 4, 5],
            [1, 3, 2, 0, 0],
            [4, 0, 0, 0, 5]]
            )
        self.mapas.append([
            [1, 0, 0, 0, 0],
            [2, 3, 0, 3, 1],
            [0, 4, 0, 0, 0],
            [0, 0, 0, 2, 4],
            [5, 0, 0, 0, 5]]
            )
        self.tablero = Tablero(self, topic, mapa=self.mapas[Escena.n])

        spyral.event.register("system.quit", spyral.director.pop, scene=self)
        spyral.event.register("Tablero.score", self.score)

        self.puntos = 0
        if gameview:
            Escena.gameview = gameview

    def mute(self, value):
        Escena.MUTE = value

    def score(self):
        if self.tablero.intentos==5:
            puntos = 1000
        elif 5<self.tablero.intentos<10:
            puntos = 500
        elif self.tablero.intentos>10:
            puntos = 100
        self.puntos += puntos

        Escena.n += 1
        if Escena.n > (len(self.mapas)-1):
            Escena.n = 0
        self.tablero.reset(self.mapas[Escena.n])

        if Escena.gameview:
            Escena.gameview.update_score(self.puntos)


def QuadraticOutTuple(start=(0, 0), finish=(0, 0)):
    """
    Linearly increasing, but with two properites instead of one.
    """
    def quadratic_easing(sprite, delta):
        return (start[0] + (finish[0] - start[0]) * (2 * delta - delta * delta),
                start[1] + (finish[1] - start[1]) * (2* delta - delta * delta))
    return quadratic_easing

def main():
    spyral.director.push(Escena())

if __name__ == "__main__":
    spyral.director.init(SIZE, fullscreen=False)
    main()
    spyral.director.run()
