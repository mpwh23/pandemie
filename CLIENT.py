#!/usr/bin/env python3
import socket
import selectors
import traceback
import tkinter as tk
from tkinter import *
import urllib.request
import math
import time
import threading
from PIL import Image, ImageTk
import inspect
import zipfile
import datetime
from pathlib import Path

from Pandemie import libclient

# BUGS
###########################################
# critical/function
# TODO - inf 2x gleiche Stadt ?

# whishlist
# TODO zähe bevölkerung abbruch?/handling nicht stabil
# TODO 'karte nicht geben' nicht über städten anzeigen
# TODO infos über Züge anzeigen (sidebar, log)
# TODO sometimes player behind infection
# TODO block Cardpile turn 8/48
# TODO action 14 + 15 for player role 5: other player must agree movement

# appearance
# TODO andere züge zeigen - hübscher zB Flugzeug
# TODO redesign Spielvorbereitung-window
# TODO game lose begründung anders (besser) darstellen

# system
# TODO  do not check toolbar
# TODO reduce tooltips
# TODO remove game_init_update
# TODO remove initupdate
# TODO raise elements in draw only if nessecary
# TODO program toolbar cleaner ,-)

########################################################################################################################
update_intervall = 3000
port = 9999
php_path = "http://moja.de/public/python/getip.php"
# -------------------------------------------------------------------------------------------------------------------- #
res = zipfile.ZipFile(str(Path(__file__).parent) + "/res/data.zip", 'r')  # TODO remove zip

trans = '@' + str(Path(__file__).parent) + '/res/tran'
full = '@' + str(Path(__file__).parent) + '/res/full'
# -------------------------------------------------------------------------------------------------------------------- #
AM_DEBUG = True # TODO False
AM_LOG = True
########################################################################################################################

# region overview ######################################################################################################
# cards:  7 : 10
# field: 17 :  8
# bars:  34 :  1

# ├ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ width ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
# ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐  ^ top-margin: 8 px
# │ C1 │ │ C2 │ │ C3 │ │ C4 │ │ C5 │ │ C6 │ │ C7 │ │ C  │  Card: -> (width-72)/8 x ((width-72)/8)/7*10
# │    │ │    │ │    │ │    │ │    │ │    │ │    │ │ new│
# └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
# ┌─────────────────────────────────────────────────────┐  ^ space: 8 px
# │                                                     │
# │                                                     │
# │               field                                 │
# │                                                     │
# │               -> width x width/17*8                 │
# │                                                     │
# │                                                     │
# │                                                     │
# └─────────────────────────────────────────────────────┘
# Status Bar  -> width x  width/34                          ^ space: 8 px
# Action Bar  -> width x  width/34                          ^ space: 8 px, v bottom-margin: 8px

# supplies
# 0	blau	006bfd
# 1	gelb	fff300
# 2	grün	189300
# 3	rot	    f10000
# Marker:
#   Ausbruchsmarker: 0-7 -> 8 = Verloren-> 4
#   Infektionsleiste:   2,2,2,3,3,4,4   -> 4
#   Heilmittel                          -> 4
# verbleibende seuchenwürfel 24 * 1/4   -> 6
# verbleibende Spielerkarten = versorgung/supplies
# Aktionsphase: 4 Aktionen (turns) ########################################################################
#  Auto/Schifffahrt:       turn  1: 1 Feld bewegen
#  Direktflug:             turn   :  Zielstadt = Karte auf der Hand -> Karte abwerfen
#  Charterflug:            turn   :  Startstadt = Karte auf der Hand -> Karte abwerfen
#  Sonderflug:             turn   :  von Forschungszentrum zu Forschungszentrum
#  Betriebsexperte (7):    turn   :  selber von Forschungszentrum in beliebige Stadt -> beliebige Karte abwerfen
#  Logistiker (5):         turn   :  bewege fremde Figur wie eigene
#  Logistiker (5):         turn   :  bewege einen beliebigen Spieler zu einem anderen Spieler
#  Forschungzentrum bauen: turn   :  Spieler in der Stadt und Stadtkarte auf der Hand -> Karte abwerfen
#                          turn   :  Wenn Betriebsexperte (7): keine Karte abwerfen
#  Seuche behandeln:       turn   :  1 Seuchenstein entfernen. Wenn geheilt, alle entfernen
#                          turn   :  Wenn Sanitäter (6): immer alle Steine entfernen
#  Wissen teilen:          turn   :  2 Spieler in Stadt, genau diese Stadtkarte kann getausscht werden
#                          turn   :  Wenn Forscherin (4): Beliebige Stadtkarten (Spieler in einer Stadt)
#  Heilmittel entdecken:   turn   :  5 gleichfarbige Karten, in Forschungszentrum
#                          turn   :  Wenn Wissenschaftlerin (1): nur 4 Karten
#  Kriesenmanager (3):     turn   :  eine Ereignisskarte aus Ablagestapel nochmal verwenden
#                          turn   :  (nur einmal und immer nur eine)
#
# Passive Fähigkeiten
#    Sanitäter (6):             Entferne alle Würfel geheilter Seuchen vom Standort (-> auch keine neuen)
#    Quarantänespezialistin(2): Am eigenen Standort und allen anliegenden Städten werden keine neuen
#                               Seuchenwürfel platziert. somit auch keine Ausbrüche
#
# Ereigniskarten:
#
# Nachschubphase: ##########################################################################################
#    2 Spielkarten nachziehen:  Kartenlimit beachten
#       ggf. Epidemie:          increase Infektionsquote
#                                eine Stadt ziehen und mit 3 Würfeln infizieren
#                               Infektionsablagestapel zurück unter Pool
#       ggf. Ausbruch:          Wenn in einer Stadt mehr als 3 Würfel einer Farbe, alle angrenzenden Städte
#                               + 1 der Ausbruchsfarbe
#                               increase Ausbruchszähler
#       ggf. Folgeausbruch:     s. Ausbruch
# Infektionsphase: #########################################################################################
#    Inizieren:                 entsprechend Infektionszähler: Anzahl Städte mit einem Seuchenwürfel
#                               infizieren
#       ggf. Ausbruch:          s.o.
#
# endregion


# region custum functions and classes
def _print(*args):
    if AM_DEBUG:
        line = ""
        for txt in args:
            line = line + " " + str(txt)
        if len(args) > 0:
            line += " > "
        line += inspect.stack()[1].__getattribute__("function")
        print(line)
        _log(line)


def _log(*args):
    if AM_LOG:
        log = open((str(Path(__file__).parent) + "/log.nfo"), "a")

        if len(args) == 0:
            log.write("\n\n")
        else:
            log.write(str(datetime.datetime.now()))
            log.write(": ")

            line = ""
            for txt in args:
                line = line + " " + str(txt)

            log.write(line)
            log.write("\n")

        log.close()


def get_role_color(role):
    switcher = {
        0: "#000000",
        1: "#d6d7df",
        2: "#245a49",
        3: "#52aedb",
        4: "#8f5735",
        5: "#cf63ae",
        6: "#ee7024",
        7: "#7ab851",
    }
    return switcher.get(role)


def get_inf_color(inum):
    switcher = {
        0: "#006bfd",  # blue
        1: "#fff300",  # yellow
        2: "#189300",  # green
        3: "#f10000",  # trd
        4: "#9d3d9e"   # purple
    }
    return switcher.get(inum)


class ResizingCanvas(Canvas):  # a subclass of Canvas for dealing with resizing of windows
    def __init__(self, parent, **kwargs):
        Canvas.__init__(self, parent, **kwargs)
        self.bind("<Configure>", self.on_resize)

        self.height = self.winfo_reqheight()
        self.width = self.winfo_reqwidth()
        self.p = parent
        self.aspect_ratio = float(self.width) / self.height

    def on_resize(self, event):
        desired_width = self.p.winfo_width()
        desired_height = float(self.p.winfo_width()) / self.aspect_ratio

        # if the window is too tall to fit, use the height as the controlling dimension
        if desired_height > self.p.winfo_height():
            desired_height = self.p.winfo_height()
            desired_width = float(self.p.winfo_height()) * self.aspect_ratio

        self.config(width=int(desired_width), height=int(desired_height))

        scale = float(int(desired_height)) / self.winfo_height()

        # this reduces scaling errors - does not fix complete :(
        if desired_height == self.winfo_height() and desired_width != self.winfo_width():
            scale = float(int(desired_width)) / self.winfo_width()

        self.scale("all", 0, 0, scale, scale)


def am_rect(x, y, w, h):
    return x, y, x + w, y + h
# endregion


class Client(tk.Tk):
    def __init__(self):
        self.sel = selectors.DefaultSelector()

        # region game variable #########################################################################################
        # player
        self.all_player_pos = [0, 0, 0, 0]
        self.all_player_cards = [[], [], [], []]
        self.all_player_name = ['', '', '', '']
        self.all_player_role = [0, 0, 0, 0]
        self.otherplayer = []

        self.TP = self.Player()

        self.logistician = 5
        self.action_48 = {}
        self.special_val = {'r3': 0, 'pos': (0, 0), 'r7': True, 'a50': []}
        # r3:   card for role3
        # r7:   extraturn for r7
        # a50:  city from 'zähe bevölkerung'

        self.visual = {}
        self.logtextcontent = ["", "", "", "", "", "", "", ""]

        # request
        self.host = ''
        self.action = 'get_init_update'
        self.value = {'v': 0}

        self.update_client = False
        self.running = False
        self.block_request = False
        self.reload = True

        # connection / loading
        self.ctrl_res_load = [0, 188, 0]  # [act load, total load, ready]
        self.ip_am = '127.0.0.1'
        self.ip_parts = self.ip_am.split(".")

        # gamestats
        self.game_STATE = "INIT"  # region ###### info ######
        # INIT:         pre game
        # WAIT:         awaits game start
        # GAME          (init over)
        # PASSIV
        # ACTION
        # SUPPLY
        # INFECT
        # LOSE_GAME
        # WIN_GAME
        # endregion
        self.localversion = 0
        self.current_player = 0
        self.outbreak = 0  # 0-7
        self.inflvl = 0  # 0-x
        self.supplies = 0  # playercard-pile
        self.infection = [24, 24, 24, 24]  # 0-24
        self.healing = [0, 0, 0, 0]  # 0 = active,  1 = healed,  2 = exterminated
        self.card_epidemie = 53
        self.gameupdatelist = {'city': [], 'cards': [], 'sidebar': [], 'playerpos': 0}

        # dimensions
        self.section_col1_w = 1
        self.section_side_w = 1

        self.section_card_h = 1
        self.section_status_h = 1
        self.section_field_h = 1
        self.section_toolbar_h = 1
        self.section_side_h = 1
        self.section_side_row_h = 1

        self.section_side_x = 0
        self.section_status_y = 0
        self.section_field_y = 0
        self.section_toolbar_y = 0

        self.city = [  # d = disease, i = infection, c = center
            {'ID':  0, 'X':  5.2, 'Y': 24.4, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [1, 12, 39, 46],          'name': 'San Francisco'},
            {'ID':  1, 'X': 14.7, 'Y': 18.5, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [0, 12, 13, 2, 3],        'name': 'Chicago'},
            {'ID':  2, 'X': 17.4, 'Y': 30.2, 'd': 0, 'i': [0, 0, 0, 0], 'c': 1, 'con': [1, 5, 14],               'name': 'Atlanta'},
            {'ID':  3, 'X': 22.1, 'Y': 18.0, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [1, 5, 4],                'name': 'Montréal'},
            {'ID':  4, 'X': 27.8, 'Y': 19.9, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [3, 5, 6, 7],             'name': 'New York'},
            {'ID':  5, 'X': 25.3, 'Y': 29.4, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [4, 3, 2, 14],            'name': 'Washington'},
            {'ID':  6, 'X': 40.6, 'Y': 25.9, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [4, 19, 24, 8, 7],        'name': 'Madrid'},
            {'ID':  7, 'X': 41.6, 'Y': 10.3, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [4, 6, 8, 9],             'name': 'London'},
            {'ID':  8, 'X': 47.2, 'Y': 18.1, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [7, 6, 24, 10, 9],        'name': 'Paris'},
            {'ID':  9, 'X': 49.1, 'Y':  7.2, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [7, 8, 10, 11],           'name': 'Essen'},
            {'ID': 10, 'X': 52.2, 'Y': 15.1, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [9, 8, 26],               'name': 'Mailand'},
            {'ID': 11, 'X': 57.3, 'Y':  4.3, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'con': [9, 26, 27],              'name': 'St. Petersburg'},
            {'ID': 12, 'X':  6.8, 'Y': 40.1, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [47, 13, 1, 0],           'name': 'Los Angeles'},
            {'ID': 13, 'X': 13.6, 'Y': 45.4, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [12, 16, 15, 14, 1],      'name': 'Mexico Stadt'},
            {'ID': 14, 'X': 22.2, 'Y': 42.9, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [13, 15, 5, 2],           'name': 'Miami'},
            {'ID': 15, 'X': 21.5, 'Y': 58.7, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [13, 16, 18, 19, 14],     'name': 'Bogotá'},
            {'ID': 16, 'X': 18.9, 'Y': 75.7, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [13, 17, 15],             'name': 'Lima'},
            {'ID': 17, 'X': 19.9, 'Y': 93.5, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [16],                     'name': 'Santiago'},
            {'ID': 18, 'X': 27.7, 'Y': 90.3, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [15, 19],                 'name': 'Buenos Aires'},
            {'ID': 19, 'X': 32.0, 'Y': 78.2, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [15, 18, 20, 6],          'name': 'Sao Paulo'},
            {'ID': 20, 'X': 46.5, 'Y': 55.8, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [19, 21, 23],             'name': 'Lagos'},
            {'ID': 21, 'X': 51.0, 'Y': 66.3, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [20, 22, 23],             'name': 'Kinshasa'},
            {'ID': 22, 'X': 55.4, 'Y': 82.6, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [21, 23],                 'name': 'Johannisburg'},
            {'ID': 23, 'X': 56.0, 'Y': 53.0, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'con': [20, 21, 22, 25],         'name': 'Khartum'},
            {'ID': 24, 'X': 48.7, 'Y': 34.6, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [6, 25, 26, 8],           'name': 'Algier'},
            {'ID': 25, 'X': 54.4, 'Y': 37.5, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [24, 23, 29, 28, 26],     'name': 'Kairo'},
            {'ID': 26, 'X': 55.5, 'Y': 24.3, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [24, 25, 28, 27, 11, 10], 'name': 'Istanbul'},
            {'ID': 27, 'X': 61.3, 'Y': 15.0, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [11, 26, 30],             'name': 'Moskau'},
            {'ID': 28, 'X': 60.7, 'Y': 32.3, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [26, 25, 29, 31, 30],     'name': 'Bagdad'},
            {'ID': 29, 'X': 61.6, 'Y': 46.8, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [25, 31, 28],             'name': 'Riad'},
            {'ID': 30, 'X': 66.3, 'Y': 22.5, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [27, 28, 31, 33],         'name': 'Teheran'},
            {'ID': 31, 'X': 67.9, 'Y': 37.9, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [28, 29, 32, 33, 30],     'name': 'Karatschi'},
            {'ID': 32, 'X': 68.5, 'Y': 49.3, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [31, 34, 33],             'name': 'Mumbai'},
            {'ID': 33, 'X': 73.3, 'Y': 33.1, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [30, 31, 32, 34, 35],     'name': 'Delhi'},
            {'ID': 34, 'X': 74.3, 'Y': 57.5, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [32, 44, 40, 35, 33],     'name': 'Chennai'},
            {'ID': 35, 'X': 78.5, 'Y': 36.9, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'con': [33, 34, 40, 41],         'name': 'Kalkutta'},
            {'ID': 36, 'X': 82.6, 'Y': 18.6, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [37, 38],                 'name': 'Peking'},
            {'ID': 37, 'X': 89.3, 'Y': 18.0, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [36, 38, 39],             'name': 'Seoul'},
            {'ID': 38, 'X': 83.2, 'Y': 29.9, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [36, 41, 42, 39, 37],     'name': 'Shanghai'},
            {'ID': 39, 'X': 94.5, 'Y': 24.3, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [37, 38, 43, 0],          'name': 'Tokyo'},
            {'ID': 40, 'X': 79.6, 'Y': 50.3, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [34, 44, 45, 41, 35],     'name': 'Bangkok'},
            {'ID': 41, 'X': 83.9, 'Y': 43.1, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [35, 40, 45, 46, 42, 38], 'name': 'Hong Kong'},
            {'ID': 42, 'X': 89.8, 'Y': 41.0, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [41, 46, 43, 38],         'name': 'Taipeh'},
            {'ID': 43, 'X': 95.1, 'Y': 36.1, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [39, 42],                 'name': 'Osaka'},
            {'ID': 44, 'X': 79.5, 'Y': 71.1, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [34, 47, 45, 40],         'name': 'Jakarta'},
            {'ID': 45, 'X': 84.2, 'Y': 61.4, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [44, 46, 41, 40],         'name': 'Ho-Chi-MinH-Stadt'},
            {'ID': 46, 'X': 91.4, 'Y': 60.6, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [45, 47, 0, 42, 41],      'name': 'Manila'},
            {'ID': 47, 'X': 95.6, 'Y': 93.1, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'con': [46, 44, 12],             'name': 'Sydney'}]

        # endregion

        tk.Tk.__init__(self)  # region UI and resources ################################################################

        # resources -> define resources here
        #              load images in thread task
        #              load_res_async(self): as it takes a while, display loading-bar
        self.img_map_raw = Image  # map (BG)
        self.img_map = ImageTk
        self.img_overlay_game_raw = Image  # map overlay (FG)
        self.img_overlay_game = ImageTk
        self.img_side_raw = Image  # sidebar
        self.img_side = ImageTk

        self.img_icon_raw = [[], [], []]  # additional icons
        self.img_icon = [[], [], []]
        self.toolbar = []
        self.img_btn_raw = [[], []]  # ok&cancle buttons
        self.img_btn = [[], []]

        self.img_char_raw = []  # character cards
        self.img_char = []
        self.img_c1_raw = []  # player cards [00..53]
        self.img_c1 = []
        self.img_c_over_raw = []  # cards overlay
        self.img_c_over = []
        self.img_c2_back_raw = Image  # infectioncard, back
        self.img_c2_back = ImageTk
        self.img_c2_raw = Image  # infectioncard, back
        self.img_c2 = ImageTk
        self.img_inf_raw = []  # infection marker: inf_0_1.png
        self.img_inf = []
        self.img_center_raw = Image  # center
        self.img_center = ImageTk
        self.img_zaeh_raw = Image  # indicator for 'zähe bevölkerung'
        self.img_zaeh = ImageTk
        self.img_p_raw = []  # player_piece
        self.img_p = []
        self.img_win_raw = Image
        self.img_win = ImageTk
        self.img_lose_raw = Image
        self.img_lose = ImageTk

        self.img_splash_raw = Image
        self.img_splash = ImageTk
        self.splash_pos = [0, 0]
        self.transparent_color = '#abcdef'

        self.img_quicktip_bg = ImageTk

        # endregion

        # region window 00 connection load
        self.LOADframe = Frame(self)
        self.load_canvas = ResizingCanvas(self.LOADframe, highlightthickness=0, bg=self.transparent_color)
        self.loading_bar = self.load_canvas.create_rectangle(am_rect(0, 0, 1, 1),
                                                             fill="#2b3e89", width=2, outline="#fff")
        # endregion

        # region window 01 connection connect
        self.CONframe = Frame(self)

        self.header = Label(self.CONframe, text="Verbindung:", font="Helvetica 24 bold")
        self.addr_frame = Frame(self.CONframe)
        self.btn_frame = Frame(self.CONframe)
        self.btn_con = Button(self.btn_frame, width="30", text='START', justify="center",
                              command=self.window_02a_game_prep)
        self.btn_recon = Button(self.btn_frame, text='reconnect',
                                command=self.window_02b_recon)
        param = dict(width="4", justify="center", font="Helvetica 32 bold")
        self.entry1 = Entry(self.addr_frame, param)
        self.l1 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.entry2 = Entry(self.addr_frame, param)
        self.l2 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.entry3 = Entry(self.addr_frame, param)
        self.l3 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.entry4 = Entry(self.addr_frame, param)
        # endregion

        # region window 02A/B preparation
        self.PREPframe = Frame(self)
        self.lbl1 = Label(self.PREPframe, text="Name", font="Helvetica 14 bold")
        self.entry_n = tk.Entry(self.PREPframe, width="16", justify="left", font="Helvetica 14 bold")
        self.btn_participate = Button(self.PREPframe, text='Teilnehmen')
        self.btn_start = Button(self.PREPframe, text='Spiel starten', state=DISABLED)
        self.lbl2 = Label(self.PREPframe, text="Deine Rolle:", font="Helvetica 12 bold")

        self.player_frame = Frame(self.PREPframe)
        self.lbl_head_player = Label(self.player_frame, text="Spieler", font="Helvetica 12 bold")
        self.lbl_head_role = Label(self.player_frame, text="Rolle", font="Helvetica 12 bold")

        self.lbl_player_name = []
        self.lbl_player_func = []
        self.lbl_player_rdy = []
        for p in range(0, 4):
            self.lbl_player_name.append(Label(self.player_frame, text="Spieler " + str(p), font="Helvetica 12"))
            self.lbl_player_func.append(Label(self.player_frame, text="-", font="Helvetica 12"))
            self.lbl_player_rdy.append(Label(self.player_frame, text=""))

        self.role_image = Label(self.PREPframe)

        self.recon_frame = Frame(self)
        self.recon_label = Label(self.recon_frame, text="Player No.: ", font="Helvetica 24 bold")
        self.entry_re = Entry(self.recon_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.btn_startrecon = Button(self.recon_frame, text='START', justify="center")
        self.recon_stat = Label(self, text="")
        # endregion

        # region window game UI
        self.game_frame = Frame(self)
        self.old_window_w = 0
        self.old_window_h = 0
        self.game_canvas = ResizingCanvas(self.game_frame, width=1, height=1, bg="#333", highlightthickness=0)

        self.i_quicktip = self.game_canvas.create_text(0, 0)
        self.i_status = self.game_canvas.create_text(0, 0)

        self.txt_status = ["", ""]
        # endregion

        self.window_00_load()

    class Player:
        def __init__(self):
            self.num = 0
            self.pos = 0
            self.cards = []
            self.name = ''
            self.role = 0
            self.card_selection = []
            self.drawcards = []
            self.range = []
            self.turns = {'sender': "", 'turn': 0, 'secondcity': False, 'LEFT': 0}
            self.xchng = {'status': "", 's': 9, 'c': 99, 'r': 9, 'b': 99, 'd': 0}  # TODO check status
            self.exchange = self.xchng

        def set_exchange(self, entry, value):
            self.exchange[entry] = value

        def reset_exchange(self):
            self.exchange = self.xchng

        def set_turns(self, entry, value):
            self.turns[entry] = value

        def set_range(self, r):
            self.range = r

        def range_append(self, r):
            self.range.append(r)

        def range_remove(self, r):
            self.range.remove(r)

        def dc_del(self, num):  # dc = drawcards = []
            del self.drawcards[num]

        def dc_append(self, cards):
            self.drawcards.append(cards)

        def set_dc(self, cards):
            self.drawcards = cards

        def cs_reset(self):  # cs = Card-Selection
            self.card_selection = []

        def cs_append(self, card):
            self.card_selection.append(card)

        def cs_remove(self, card):
            self.card_selection.remove(card)

        def set_role(self, rolein):
            self.role = rolein[self.num]

        def set_name(self, namein):
            self.name = namein[self.num]

        def set_cards(self, cardsin):
            self.cards = cardsin[self.num]

        def set_pos(self, posin):
            self.pos = posin[self.num]

        def set_num(self, numin):
            self.num = numin

    # region ###### preparation ########################################################################################
    def window_00_load(self):
        def window_00_load_async():

            _print("INIT", "  start")
            self.config(cursor="wait")
            # connection
            # try to get ip for server from php-script
            self.ip_am = urllib.request.urlopen(php_path).read().decode('utf8').strip()
            self.ip_parts = self.ip_am.split(".")

            self.ctrl_res_load[2] = 1

            self.img_map_raw = Image.open(res.open("mat/world.png"))
            self.img_map = ImageTk.PhotoImage(self.img_map_raw)
            self.ctrl_res_load[0] += 1

            self.img_overlay_game_raw = Image.open(res.open("mat/namen.png"))
            self.img_overlay_game = ImageTk.PhotoImage(self.img_overlay_game_raw)
            self.ctrl_res_load[0] += 1

            self.img_side_raw = Image.open(res.open("mat/sidebar.png"))
            self.img_side = ImageTk.PhotoImage(self.img_side_raw)
            self.ctrl_res_load[0] += 1

            self.img_center_raw = Image.open(res.open("mat/center.png"))
            self.img_center = ImageTk.PhotoImage(self.img_center_raw)
            self.ctrl_res_load[0] += 1

            self.img_zaeh_raw = Image.open(res.open("mat/zaeh.png"))
            self.img_zaeh = ImageTk.PhotoImage(self.img_zaeh_raw)
            self.ctrl_res_load[0] += 1

            for c in range(0, 55):
                self.img_c1_raw.append(Image.open(res.open("cards/c1_" + "{:02d}".format(c) + ".png")))
                self.img_c1.append(ImageTk.PhotoImage(self.img_c1_raw[c]))
                self.ctrl_res_load[0] += 1

            for c in range(0, 17):
                self.img_c_over_raw.append(Image.open(res.open("cards/card_overlay_" + "{:01d}".format(c) + ".png")))
                self.img_c_over.append(ImageTk.PhotoImage(self.img_c_over_raw[c]))
                self.ctrl_res_load[0] += 1

            self.img_c2_back_raw = Image.open(res.open("cards/c2_0.png"))
            self.img_c2_back = ImageTk.PhotoImage(self.img_c2_back_raw)
            self.ctrl_res_load[0] += 1

            # TODO remove
            self.img_c2_raw = Image.open(res.open("cards/c2_overlay.png"))
            self.img_c2 = ImageTk.PhotoImage(self.img_c2_raw)
            self.ctrl_res_load[0] += 1

            self.img_win_raw = Image.open(res.open("mat/win.png"))
            self.img_win = ImageTk.PhotoImage(self.img_win_raw)
            self.ctrl_res_load[0] += 1

            self.img_lose_raw = Image.open(res.open("mat/lose.png"))
            self.img_lose = ImageTk.PhotoImage(self.img_lose_raw)
            self.ctrl_res_load[0] += 1

            for c in range(0, 8):
                self.img_char_raw.append(Image.open(res.open("cards/char_" + str(c) + ".png")))
                self.img_char.append(ImageTk.PhotoImage(self.img_char_raw[c].resize((350, 500), Image.ANTIALIAS)))
                self.ctrl_res_load[0] += 1

            self.img_inf_raw = [
                [Image.open(res.open("mat/inf_" + str(x) + "_" + str(y + 1) + ".png")) for x in range(4)]
                for y in range(4)]
            self.ctrl_res_load[0] += 8  # add 8 for 16 elements
            self.img_inf = [[[ImageTk.PhotoImage(self.img_inf_raw[x][y]) for x in range(4)] for y in range(4)] for z in
                            range(3)]
            self.ctrl_res_load[0] += 8  # add second 8 for 16 elements

            for p in range(0, 7):
                self.img_p_raw.append(Image.open(res.open("mat/player_" + str(p + 1) + ".png")))
                self.img_p.append(ImageTk.PhotoImage(self.img_p_raw[p]))
                self.ctrl_res_load[0] += 1

            for ico in range(0, 23):
                self.img_icon_raw[0].append(Image.open(res.open("mat/icon_" + str("%02d" % (ico,)) + "_0.png")))
                self.img_icon[0].append(ImageTk.PhotoImage(self.img_icon_raw[0][ico]))
                self.ctrl_res_load[0] += 1
                self.img_icon_raw[1].append(Image.open(res.open("mat/icon_" + str("%02d" % (ico,)) + "_1.png")))
                self.img_icon[1].append(ImageTk.PhotoImage(self.img_icon_raw[1][ico]))
                self.ctrl_res_load[0] += 1
                self.img_icon_raw[2].append(Image.open(res.open("mat/icon_" + str("%02d" % (ico,)) + "_2.png")))
                self.img_icon[2].append(ImageTk.PhotoImage(self.img_icon_raw[2][ico]))
                self.ctrl_res_load[0] += 1

            for btn in range(0, 3):
                self.img_btn_raw[0].append(Image.open(res.open("mat/button_" + str("%01d" % (btn,)) + "_0.png")))
                self.img_btn[0].append(ImageTk.PhotoImage(self.img_btn_raw[0][btn]))
                self.ctrl_res_load[0] += 1
                self.img_btn_raw[1].append(Image.open(res.open("mat/button_" + str("%01d" % (btn,)) + "_1.png")))
                self.img_btn[1].append(ImageTk.PhotoImage(self.img_btn_raw[1][btn]))
                self.ctrl_res_load[0] += 1

            self.config(cursor="")
            # loading done
            _print("INIT", "  done ")
            self.ctrl_res_load[2] = 3

        if self.ctrl_res_load[0] == 0:  # region INIT
            _print("INIT")
            self.wm_attributes('-transparentcolor', self.transparent_color, '-fullscreen', True)

            self.title("Pandemie")
            self.LOADframe.pack(fill="both", expand=True)
            self.load_canvas.pack(fill="both", expand=True)
            self.img_splash_raw = Image.open(res.open("mat/splash.png"))
            self.img_splash = ImageTk.PhotoImage(self.img_splash_raw)
            self.update()

            self.splash_pos = [self.winfo_width() / 2, self.winfo_height() / 2]

            self.load_canvas.create_image(
                self.splash_pos,
                image=self.img_splash,
                anchor=CENTER,
                tags="splash_bg")

            self.load_canvas.create_text(
                self.splash_pos[0] + 18,
                self.splash_pos[1] - 10,
                text='connect to server...', anchor='center', tags="loadingtext")
            self.load_canvas.create_rectangle(self.load_canvas.bbox("loadingtext"),
                                              fill="#fff", outline='#fff', tags="bg")
            self.load_canvas.tag_lower("bg", "loadingtext")

            self.load_canvas.coords(self.loading_bar,
                                    self.splash_pos[0] + 35 - 290,
                                    self.splash_pos[1] + 167 - 150,
                                    self.splash_pos[0] + 35 + 1 - 290,
                                    self.splash_pos[1] + 167 + 7 - 150)
            self.load_canvas.tag_raise(self.loading_bar, "bg")

            self.ctrl_res_load[0] += 1  # end init
            thread1 = threading.Thread(target=window_00_load_async)
            thread1.start()
        # endregion

        if self.ctrl_res_load[2] == 1:  # switch text after connectiondata is loaded
            self.load_canvas.itemconfigure("loadingtext", text="loading resources...")
            self.ctrl_res_load[2] = 2

        if self.ctrl_res_load[2] == 2:  # load rescources and display bar
            self.load_canvas.coords(self.loading_bar, am_rect(self.splash_pos[0] + 35 - 290,
                                                              self.splash_pos[1] + 167 - 150,
                                                              500 * self.ctrl_res_load[0] / self.ctrl_res_load[1],
                                                              7))

        if self.ctrl_res_load[2] == 3:  # leave loop and start connection window
            self.after(500, self.window_01_connect)
        else:  # loop self
            self.after(1, self.window_00_load)

    def window_01_connect(self):
        _print("INIT")
        self.LOADframe.destroy()

        self.wm_attributes('-fullscreen', False)
        self.update()
        self.title("Pandemie | Verbindung")

        if AM_DEBUG:
            self.geometry("512x140+{}+{}".format(758, 1))
        else:
            self.geometry("512x140+{}+{}".format(int(self.splash_pos[0] - 256), int(self.splash_pos[1] - 70)))

        self.entry1.insert(0, self.ip_parts[0])
        self.entry2.insert(0, self.ip_parts[1])
        self.entry3.insert(0, self.ip_parts[2])
        self.entry4.insert(0, self.ip_parts[3])

        self.CONframe.pack(fill=BOTH)
        self.header.pack(side=TOP)
        self.addr_frame.pack(side=TOP)
        self.btn_frame.pack(side=TOP, fill=BOTH)
        self.btn_con.pack(side="right", padx=(5, 28), pady=5)
        self.btn_recon.pack(side="left", padx=(28, 5), pady=5)
        self.entry1.pack(side="left")
        self.l1.pack(side="left")
        self.entry2.pack(side="left")
        self.l2.pack(side="left")
        self.entry3.pack(side="left")
        self.l3.pack(side="left")
        self.entry4.pack(side="left")

        self.btn_con.focus_set()
        self.btn_con.bind('<Return>', self.window_02a_game_prep)
        self.btn_recon.bind('<Return>', self.window_02b_recon)

    def window_02a_game_prep(self, *event):
        def btn_init_signin(*event):
            _print("INIT", "BTN")
            playername = self.entry_n.get()
            if playername != "":
                self.entry_n.configure(state=DISABLED)
                self.btn_participate.configure(state=DISABLED)
                self.action = "player_signin"
                self.value = {'v': self.localversion, 'player_name': playername.strip()}

                self.btn_start.focus_set()
                self.entry_n.unbind('<Return>')
                self.btn_start.bind('<Return>', btn_init_player_rdy)

        def btn_init_player_rdy(*event):
            _print("INIT", "BTN")
            self.btn_start.configure(bg="SeaGreen1", text="Warte auf andere Spieler", state=DISABLED)
            self.game_STATE = "WAIT"
            self.action = 'player_rdy'
            self.value = {'v': self.localversion, 'player_num': self.TP.num}

        _print("INIT")

        # global client_host
        self.host = self.entry1.get() + '.' + self.entry2.get() + '.' + self.entry3.get() + '.' + self.entry4.get()

        self.CONframe.destroy()

        self.title("Spielvorbereitung")

        if AM_DEBUG:
            self.geometry("700x600+758+1")
        else:
            self.geometry("700x600+{}+{}".format(int(self.splash_pos[0] - 350), int(self.splash_pos[1] - 300)))

        self.PREPframe.grid()
        self.lbl1.grid(row=0, column=1, padx=5, pady=18, sticky=E)
        self.entry_n.grid(row=0, column=2, padx=5, pady=18, sticky=W + E)
        self.entry_n.focus_set()
        self.entry_n.bind('<Return>', btn_init_signin)

        self.btn_participate.configure(command=btn_init_signin)
        self.btn_participate.grid(row=0, column=3, padx=5, pady=18, sticky=W)
        self.btn_start.configure(command=btn_init_player_rdy)
        self.btn_start.grid(row=0, column=4, padx=5, pady=18, sticky=W)
        self.lbl2.grid(row=1, column=1, padx=5, pady=0, sticky=W + S, columnspan=2)

        self.role_image = Label(self.PREPframe, image=self.img_char[0])
        self.role_image.grid(row=2, column=1, padx=5, pady=5, columnspan=2)

        self.player_frame.grid(row=1, column=3, padx=5, pady=5, sticky=N, rowspan=2, columnspan=3)
        self.lbl_head_player.grid(row=1, column=3, padx=5, pady=0, sticky=E)
        self.lbl_head_role.grid(row=1, column=4, padx=5, pady=0, sticky=W)

        for p in range(0, 4):
            self.lbl_player_name[p].grid(row=2 + p, column=3, padx=5, pady=5, sticky=E)
            self.lbl_player_func[p].grid(row=2 + p, column=4, padx=5, pady=5, sticky=E)
            self.lbl_player_rdy[p].grid(row=2 + p, column=5, padx=5, pady=5, sticky=E)

        self.start_main()

    def window_02b_recon(self, event=None):
        def btn_init_recon():
            _print("INIT", "BTN")
            try:
                num = int(self.entry_re.get())
                if 0 <= num < 4:
                    _print("reconnect player:", str(num))

                    self.TP.set_num(num)

                    self.action = 'recon'
                    # self.value = {'v': self.localversion, 'num': num}
                    self.recon_frame.destroy()
                    self.start_main()
                else:
                    self.recon_stat.config(text="invalid player, enter 'Player No.' from 0 to 3")
            except ValueError:
                self.recon_stat.config(text="invalid entry, enter numeric value from 0 to 3")

        # global client_host
        self.host = self.entry1.get() + '.' + self.entry2.get() + '.' + self.entry3.get() + '.' + self.entry4.get()
        _print("INIT", "reconnect", self.host)

        self.CONframe.destroy()

        self.title("Reconnect")

        if AM_DEBUG:
            self.entry_re.insert(0, "0")

        self.recon_frame.pack(side=TOP, pady=(40, 0))
        self.recon_label.pack(side="left")
        self.entry_re.pack(side="left")
        self.btn_startrecon.pack(side="right", padx=(10, 0), pady=5)
        self.recon_stat.pack(side="bottom")

        self.btn_startrecon.focus_set()
        self.btn_startrecon.configure(command=btn_init_recon)
        self.btn_startrecon.bind('<Return>', btn_init_recon)
    # endregion

    # region ###### connection #########################################################################################
    def start_main(self):
        _print("INIT")
        self.send_request()
        self.running = True
        threading.Thread(target=self.delay_request).start()

    def start_connection(self, shost, sport, request):
        addr = (shost, sport)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        message = libclient.Message(self.sel, sock, addr, request)
        self.sel.register(sock, events, data=message)

    def _update(self, *args):
        if len(args) > 0:
            self.action = args[0]
        self.update_client = True
        self.block_request = True
        if self.game_STATE == "LOSE_GAME":
            self.config(cursor="pirate")
        elif self.game_STATE == "WIN_GAME":
            self.config(cursor="heart")
        else:
            self.config(cursor="watch")

    def delay_request(self):
        u = update_intervall  # default 3000
        while u > 0:
            u -= 40
            time.sleep(1 / 25)
            if self.update_client:
                self.update_client = False
                u = 0

        if self.running:
            self.send_request()
            threading.Thread(target=self.delay_request).start()

    def send_request(self):

        def create_request(raction, value):
            return dict(
                type="text/json",
                encoding="utf-8",
                content=dict(action=raction, value=value),
            )

        request = create_request(self.action, self.value)
        self.start_connection(self.host, port, request)

        try:
            while True:
                events = self.sel.select(timeout=1)
                for key, mask in events:
                    message = key.data
                    try:
                        message.process_events(mask)
                        if mask == 1:
                            self.game_engine(message.get_response())
                    except Exception as e:
                        _print(
                            "main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}",
                            e
                        )
                        self.report_error("Player " + str(self.TP.num) + " Request Error:")
                        message.close()
                # Check for a socket being monitored to continue.
                if not self.sel.get_map():
                    break
        except KeyboardInterrupt:
            pass

    def report_error(self, error):
        _print("[" + str(self.TP.num) + "]",
               "ERROR",
               error)
        self.value = {'v': self.localversion,
                      'e': error}
        self._update('error')
    # endregion

    # region ------ INIT -----------------------------------------------------------------------------------------------
    def game_init_update(self, args):
        def get_role_name(num):
            switcher = {
                0: "-",
                1: "Wissenschaftlerin",
                2: "Quarantäne-Spezialistin",
                3: "Krisenmanager",
                4: "Forscherin",
                5: "Logistiker",
                6: "Sanitäter",
                7: "Betriebsexperte",
            }
            return switcher.get(num, "Invalid request")

        # update version
        self.localversion = args.get("v")

        # player_name / player role
        self.all_player_name = args.get("player")
        self.TP.set_name(args.get("player"))
        self.all_player_role = args.get("player_role")
        self.TP.set_role(args.get("player_role"))

        for p in range(0, 4):
            self.lbl_player_name[p].configure(text=args.get("player")[p])
            self.lbl_player_func[p].configure(text=get_role_name(args.get("player_role")[p]))
            if args.get("player_rdy")[p] == 1:
                self.lbl_player_rdy[p].configure(text="- bereit -", font=('Helvetica', 12, 'bold'), fg="#006600")

        return 'getVersion'

    def game_init_player_set(self, args):
        _print("INIT")

        # playernum
        self.TP.set_num(args.get("player_num"))  # [0..4]
        _print("player_set: thisplayer_num:", str(self.TP.num))

        # player_name / player role
        self.all_player_role = args.get("player_role")
        self.TP.set_role(args.get("player_role"))
        self.all_player_name = args.get("player")
        self.TP.set_name(args.get("player"))

        if self.TP.num > 3:
            self.lbl2.configure(text="Zu viele Spieler")
        else:
            self.btn_start.configure(state=NORMAL)
            self.role_image.configure(image=self.img_char[self.TP.role])

        return self.game_init_update(args)

    def game_init_recon(self, args):
        _print("INIT")
        self.localversion = 0  # -> force update after recon
        self.all_player_name = args.get("player")
        self.TP.set_name(args.get("player"))
        self.all_player_role = args.get("player_role")
        self.TP.set_role(args.get("player_role"))
        self.game_STATE = args.get("state")
        self.game_STATE = "WAIT"

        return self.game_init_execute_game()

    def game_init_execute_game(self, *args):
        if self.game_STATE == "WAIT":
            _print("INIT")
            self.PREPframe.destroy()

            self.title("Pandemie")  # region UI

            # user32 = ctypes.windll.user32
            # win_x = user32.GetSystemMetrics(0) - 20
            # win_y = user32.GetSystemMetrics(1) - 60

            win_x = self.winfo_screenwidth() - 15
            win_y = self.winfo_screenheight() - 80

            if AM_DEBUG:
                win_x = int(win_x / 2.2)
                win_y = int(win_y / 2.2)
                if self.TP.num == 0:
                    self.geometry(str(win_x) + 'x' + str(win_y) + '+950+2')
                elif self.TP.num == 1:
                    self.geometry(str(win_x) + 'x' + str(win_y) + '+950+780')
                elif self.TP.num == 2:
                    self.geometry(str(win_x) + 'x' + str(win_y) + '+1+2')
                elif self.TP.num == 3:
                    self.geometry(str(win_x) + 'x' + str(win_y) + '+1+780')
            else:
                self.geometry(str(win_x) + 'x' + str(win_y) + '+0+0')

            self.game_STATE = 'PASSIV'
            self.localversion = 0
            self.value = {'v': 0}
        return 'get_update'
    # endregion

    # region ###### game ###############################################################################################
    def game_engine(self, m_response):

        if m_response is not None:
            m_version = m_response.get("v") if "v" in m_response else None
        else:
            m_version = None

        if self.TP.turns['sender'] != "":
            _print("[" + str(self.TP.num) + "]",
                   self.game_STATE,
                   "Turn[" + str(self.TP.turns['turn']) + "]",
                   "sender[" + str(self.TP.turns['sender']) + "]")

        # update game button
        if self.TP.turns['turn'] == 15 and self.TP.turns['sender'] == "BTN":
            self.draw_city_highlight()
            self.localversion = 0
            self.reload = True

        # region MANAGE requests #######################################################################################
        if m_response.get("R"):
            switcher = {
                # RESPONSE after request ------------------------------------------------
                "init_update":  self.game_init_update,
                "player_set":   self.game_init_player_set,
                "recon":        self.game_init_recon,
                "update":       self.game_update,
                "new_cards":    self.receive_card,
                # GLOBAL RESPONSE - STATE-CHANGE ----------------------------------------
                "GAME":         self.game_init_execute_game
            }
            func = switcher.get(m_response.get("R"), lambda r: None)  # returns new action for request
            newaction = func(m_response)  # execute

            func = switcher.get(m_response.get("state"), lambda r: None)

            stateaction = func(m_response)

            if stateaction is not None:  # override
                newaction = stateaction

            if newaction is not None:
                self._update(newaction)
        # endregion
        # region MANAGE version ########################################################################################
        else:
            if m_version is not None:

                if m_version != self.localversion:
                    if self.game_STATE == 'INIT' or self.game_STATE == 'WAIT':
                        self._update('get_init_update')
                    elif self.game_STATE in {'PASSIV', 'ACTION', 'SUPPLY', 'EPIDEMIE', 'INFECT'}:
                        self.value = {'v': self.localversion}
                        self._update('get_update')
                    else:
                        _print("[" + str(self.TP.num) + "]",
                               "FAILURE: unknown game status")
                        self._update('getVersion')
                        self.txt_status[0] = "FAILURE: unknown game status"
                else:
                    # unblock
                    self.block_request = False
                    self.config(cursor="")
                    self.value = {'v': self.localversion}
                    self.action = 'getVersion'
            else:
                _print("[" + str(self.TP.num) + "]",
                       "FAILURE: Game Engine - No response")
        # endregion
        # region MANAGE state ##########################################################################################

        # region ###### actions for any state
        # region ACTIONCARD ========================================================================================== #
        # ---  6 - select ACTIONCARD --------------------------------------------------------------------------------- #
        if self.TP.turns['turn'] == 6:
            if self.TP.turns['sender'] == "BTN":
                self.txt_status[1] = "Keine Aktionskarte vorhanden."
                self.TP.cs_reset()
                for c in self.TP.cards:
                    if c > 47:
                        self.txt_status[1] = "Wähle Aktionskarte aus."
                        self.TP.cs_append(self.TP.cards.index(c))
                        self.draw_card_highlight([self.TP.cards.index(c)],
                                                 "G",
                                                 "actioncard")
                if self.special_val['r3'] != 0:
                    self.txt_status[1] = "Wähle Aktionskarte aus."
                    self.TP.cs_append(9)
                    self.draw_card_highlight([9],
                                             "G",
                                             "actioncard")
            if self.TP.turns['sender'] == "CARD":
                self.TP.set_turns('sender', "BTN")  # set card as btn
                if self.TP.turns['card'] < 8:
                    self.TP.set_turns('turn', self.TP.cards[self.TP.turns['card']])
                else:
                    self.TP.set_turns('turn', self.special_val['r3'])
        # --- 48 - ACTIONCARD - Prognose ----------------------------------------------------------------------------- #
        if self.TP.turns['turn'] == 48:
            if self.TP.turns['sender'] == "BTN":  # initialize action
                self.value = {'v': self.localversion,
                              'ac': 48,
                              'turn': "request",
                              'player': self.TP.num}
                self._update('actioncard')

            if self.TP.turns['sender'] == "response":
                # tag 'BTN_48' to identify click
                # tag 'popup' to delete all elements related temp display
                firstsix = self.TP.turns['args']
                if len(firstsix) > 0:
                    self.txt_status[1] = "Sortiere Karten neu"
                    self.action_48['cards'] = firstsix

                    self.draw_cards(firstsix, 48)
                else:
                    self.txt_status[1] = "Keine Karten zu sortieren"

            if self.TP.turns['sender'] == "exec48":
                for child in self.winfo_children():  # unbind all
                    child.unbind("<Enter>")
                    child.unbind("<Motion>")
                self.game_canvas.delete("popup")
                self.dismiss_tooltip()
                self.txt_status[1] = ""
                self.value = {'v': self.localversion,
                              'ac': 48,
                              'turn': "exec",
                              'cards': self.action_48['cards'],
                              'player': self.TP.num}
                self._update('actioncard')
            if self.TP.turns['sender'] == "cancel48":
                for child in self.winfo_children():  # unbind all
                    child.unbind("<Enter>")
                    child.unbind("<Motion>")
                self.game_canvas.delete("popup")
                self.dismiss_tooltip()
                self.txt_status[1] = ""
                self.value = {'v': self.localversion,
                              'ac': 48,
                              'turn': "cancel",
                              'cards': self.action_48['cards'],
                              'player': self.TP.num}
                self._update('actioncard')
        # --- 49 - ACTIONCARD - Freiflug ----------------------------------------------------------------------------- #
        if self.TP.turns['turn'] == 49:
            if self.TP.turns['sender'] == "BTN":  # initialize action
                self.draw_card_highlight(None)
                self.dismiss_tooltip()
                self.txt_status[1] = "Wähle Spieler aus."
                selected_player = []
                for num, name in enumerate(self.all_player_name):
                    if name != '':
                        selected_player.append(num)
                self.draw_player_selection(selected_player, "action49")
            if self.TP.turns['sender'] == "PLAY":
                self.game_canvas.delete("popup")
                self.txt_status[1] = "Wähle Zielstadt aus."
                allcitys = [x for x in range(48)]
                allcitys.remove(self.all_player_pos[self.TP.turns['player']])
                self.draw_city_highlight(allcitys)
            if self.TP.turns['sender'] == "CITY":
                self.draw_city_highlight()
                self.dismiss_tooltip()
                self.txt_status[1] = ""
                # update server
                self.value = {'v': self.localversion,
                              'player': self.TP.num,
                              'moveplayer': self.TP.turns['player'],
                              'moveto': self.TP.turns['city'],
                              'usedcards': [49]}
                self._update('player_move')
        # --- 50 - ACTIONCARD - zähe Bevölkerung -------------------------------------------------------------------- #
        if self.TP.turns['turn'] == 50:
            if self.TP.turns['sender'] == "BTN":  # initialize action
                self.draw_card_highlight(None)
                self.TP.cs_reset()
                self.txt_status[1] = "Lade Städte..."

                self.value = {'v': self.localversion,
                              'ac': 50,
                              'turn': "request",
                              'player': self.TP.num}
                self._update('actioncard')
            if self.TP.turns['sender'] == "response":
                selection = self.TP.turns['args']
                self.draw_city_highlight(selection, "#ff00ff")
                self.txt_status[1] = "Wähle zu entfernende Stadtkarte aus"
            if self.TP.turns['sender'] == "CITY":
                self.draw_city_highlight()
                self.dismiss_tooltip()
                self.txt_status[1] = ""
                self.value = {'v': self.localversion,
                              'ac': 50,
                              'turn': "exec",
                              'city': self.TP.turns['city'],
                              'player': self.TP.num}
                self._update('actioncard')
        # --- 51 - ACTIONCARD - staatliche Subvention ---------------------------------------------------------------- #
        if self.TP.turns['turn'] == 51:
            if self.TP.turns['sender'] == "BTN":  # initialize action
                self.draw_card_highlight(None)
                self.dismiss_tooltip()
                self.txt_status[1] = "Wähle Stadt für Forschungszentrum aus."
                citysel = []
                for num, c in enumerate(self.city):
                    if not c.get('c'):
                        citysel.append(num)
                self.draw_city_highlight(citysel)
                if len(citysel) < 43:
                    # already six centers on the field

                    self.TP.set_turns('maxcenter', True)
                else:
                    self.TP.set_turns('maxcenter', False)

                self.TP.set_turns('secondcity', False)

            if self.TP.turns['sender'] == "CITY" and not self.TP.turns['secondcity']:
                self.draw_city_highlight()

                if self.TP.turns['maxcenter']:
                    self.TP.set_turns('1stcity', self.TP.turns['city'])
                    self.TP.set_turns('secondcity', True)
                    self.TP.set_turns('sender', "")
                    citysel = []
                    for num, c in enumerate(self.city):
                        if c.get('c'):
                            citysel.append(num)
                    self.draw_city_highlight(citysel)
                    self.txt_status[1] = "Wähle Center zum verschieben"
                else:
                    self.draw_city_highlight()
                    self.txt_status[1] = ""
                    # build center
                    self.value = {'v': self.localversion,
                                  'ac': 51,
                                  'city': self.TP.turns['city'],
                                  'player': self.TP.num,
                                  'center_removed': None}
                    self._update('actioncard')

            if self.TP.turns['sender'] == "CITY" and self.TP.turns['secondcity']:
                self.draw_city_highlight()
                self.txt_status[1] = ""
                self.TP.set_turns('secondcity', False)
                # build center
                self.value = {'v': self.localversion,
                              'ac': 51,
                              'city': self.TP.turns['1stcity'],
                              'player': self.TP.num,
                              'center_removed': self.TP.turns['city']}
                self._update('actioncard')
        # --- 52 - ACTIONCARD - ruhige Nacht ------------------------------------------------------------------------- #
        if self.TP.turns['turn'] == 52:
            if self.TP.turns['sender'] == "BTN":  # initialize action
                self.draw_card_highlight(None)
                self.dismiss_tooltip()
                self.txt_status[1] = "Die nächste Infektionsphase wird übersprungen."
                self.value = {'v': self.localversion,
                              'ac': 52,
                              'player': self.TP.num}
                self._update('actioncard')
        # endregion

        # -- 500 - exchange card - request card ---------------------------------------------------------------------- #
        if self.TP.turns['turn'] == 500:
            # choose card to give or decline, this player is sender
            if self.TP.turns['sender'] == "CARD":
                print(">>> X >>> 500 CARD", self.TP.exchange)
                self.TP.exchange['c'] = self.TP.cards[self.TP.turns['card']]

                self.TP.set_exchange('status', "execute")
                self.TP.set_exchange('d', 0)
                self.value = {'v': self.localversion,
                              'exchange': self.TP.exchange}
                self._update('card_exchange')
                self.game_canvas.delete("popup")
            elif self.TP.turns['sender'] == "BTN_":
                print(">>> X >>> 500 BTN_", self.TP.turns)
                # decline request
                self.TP.set_exchange('status', "execute")
                self.TP.set_exchange('d', 1)
                self.value = {'v': self.localversion,
                              'exchange': self.TP.exchange}
                self._update('card_exchange')
                self.game_canvas.delete("popup")

                # TODO check
                self.txt_status[1] = ""
                #self.draw_card_highlight()
                self.draw_card_highlight(None)
                self.draw_city_highlight()
                self.game_canvas.delete("popup")
        # -- 501 - exchange card - receive card ---------------------------------------------------------------------- #
        if self.TP.turns['turn'] == 501:
            if self.TP.turns['sender'] == "CARD":
                print(">>> X >>> 501 CARD", self.TP.exchange)
                playercard_decline = 0

                if self.TP.turns['card'] < len(self.TP.cards):  # replace card
                    self.TP.set_exchange('p', self.TP.cards[self.TP.turns['card']])
                elif self.TP.turns['card'] == 7:  # decline card
                    playercard_decline = 1
                self.TP.dc_del(0)
                self.gameupdatelist['cards'].append(7)

                self.TP.set_exchange('status', "execute")
                self.TP.set_exchange('d', playercard_decline)
                self.value = {'v': self.localversion,
                              'exchange': self.TP.exchange}

                self._update('card_exchange')

                # TODO check
                self.txt_status[1] = ""
                self.draw_card_highlight()
                self.draw_card_highlight(None)
                self.draw_city_highlight()
                self.game_canvas.delete("popup")
        # endregion

        if self.game_STATE == "PASSIV" and self.localversion != 0:  # awaits turn
            if self.current_player == self.TP.num:  # init STATE: action
                self.TP.set_turns('turn', 0)
                self.special_val['r7'] = True  # reset player 7 turn 157 (only once)
                # self.exchange_block = False
                self.txt_status[1] = "Du bist am Zug."
                self.game_STATE = "ACTION"
            else:
                self.txt_status[0] = self.all_player_name[self.current_player] + " ist am Zug."

        if self.game_STATE == "ACTION":
            # awaits click to set action, execute action, STATE ends when player_turns_left = 0
            if self.TP.turns['LEFT'] > 0:
                # region ###### set statustext ######
                if self.TP.turns['LEFT'] > 1:
                    self.txt_status[0] = "Aktionsphase: " + str(self.TP.turns['LEFT']) + \
                                      " Aktionen verbleibend."
                else:
                    self.txt_status[0] = "Aktionsphase: Eine Aktion verbleibend."
                # endregion
                # region ###### actions ######
                # region ---  2 - build center ----------------------------------------------------------------------- #
                if self.TP.turns['turn'] == 2:
                    if self.TP.turns['sender'] != "":
                        # init var
                        pos = self.TP.pos
                        center = []
                        for anz, c in enumerate(self.city):
                            if c.get("c"):
                                center.append(anz)

                        if pos in self.TP.cards or \
                                self.TP.role == 7:  # betriebsexperte

                            if self.city[pos]['c'] != 1:
                                if len(center) < 6:  # build new center
                                    # update server
                                    self.value = {'v': self.localversion,
                                                  'player': self.TP.num,
                                                  'center_new': pos,
                                                  'center_removed': None
                                                  }
                                    self._update('center')
                                else:  # move existing center
                                    if self.TP.turns['sender'] == "BTN":  # highlight for movement
                                        self.draw_city_highlight(center)
                                        self.txt_status[1] = "Wähle Center zum verschieben"
                                    if self.TP.turns['sender'] == "CITY":  # move center
                                        # update server
                                        self.value = {'v': self.localversion,
                                                      'player': self.TP.num,
                                                      'center_new': pos,
                                                      'center_removed': self.TP.turns['city']
                                                      }
                                        self._update('center')
                            else:
                                self.txt_status[1] = "Nur ein Forschungscenter möglich."
                        else:
                            self.txt_status[1] = "Stadtkarte benötigt"
                # endregion
                # region ---  3 - cure disease ----------------------------------------------------------------------- #
                if self.TP.turns['turn'] == 3:
                    if self.TP.turns['sender'] == "BTN":
                        check = 0
                        dis = None
                        for c in range(0, 4):
                            if self.city[self.TP.pos]['i'][c] > 0:
                                check += 1
                                dis = c
                        if check == 0:
                            self.txt_status[1] = "Keine Krankheit zu behandeln."
                        elif check == 1:
                            # only 1 disease in city
                            # update server
                            self.value = {'v': self.localversion,
                                          'player': self.TP.num,
                                          'disease': dis}
                            self._update('update_inf')
                        else:
                            # several diseases, select wich to cure
                            self.draw_disease_selection(self.TP.pos)
                    if self.TP.turns['sender'] == "DIS_":
                        # update game
                        self.game_canvas.delete("popup")
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.TP.num,
                                      'disease': self.TP.turns['disease']}
                        self._update('update_inf')
                # endregion
                # region ---  4 - share knowledge -------------------------------------------------------------------- #
                if self.TP.turns['turn'] == 4:
                    # order:
                    #    1. BTN -> reset exchange settings
                    #    2. select s or r OR display choose -> after choose select s or r
                    #    3. CARD: if s is selcted, select c to send OR if r is selected, select b to burn
                    #    4. PALYER:

                    # build variable: self.TP.exchange:
                    # {'status': "", 's': 9, 'c': 99, 'r': 9, 'b': 99, 'd': 0} TODO check
                    # s: sender
                    # c: card
                    # r: receiver
                    # b: burn
                    # d: decline

                    # init exchange
                    if self.TP.turns['sender'] == "BTN":
                        print(">>> X >>> 4 BTN", self.TP.turns)
                        # reset exchange state
                        self.TP.cs_reset()
                        self.TP.reset_exchange()
                        self.draw_card_highlight(None)
                        self.draw_player_selection()

                        if self.check_exchange():
                            if self.check_exchange("send") and not self.check_exchange("receive"):  # send only
                                self.TP.set_exchange('s', self.TP.num)

                                self.txt_status[1] = "Wähle Karte zum geben aus."
                                self.draw_card_highlight(self.city2card(self.check_exchange("send_cards")), "G")
                                # select card, then receiver ..................................... -> player is sender
                            elif not self.check_exchange("send") and self.check_exchange("receive"):  # receive only
                                self.TP.set_exchange('r', self.TP.num)
                                print(">>> X >>> Wähle Platz für neue Karte aus.", self.TP.exchange)
                                self.txt_status[1] = "Wähle Platz für neue Karte aus."
                                self.draw_card_highlight(0, 0, "select_space")
                                # select space, then sender, card can not be set ................. -> player is receiver
                            else:  # send or receive
                                self.txt_status[1] = "Wähle Aktion aus."
                                self.game_canvas.create_image(
                                    self.section_col1_w - math.floor(self.section_toolbar_h) * 13 - 4 + math.floor(self.section_toolbar_h) / 2,
                                    self.section_toolbar_y - 16,
                                    image=self.img_c_over[10],
                                    activeimage=self.img_c_over[11],
                                    anchor=SE,
                                    tags=("BTN_401", "popup", "toclick", "choose")
                                )
                                self.game_canvas.tag_bind("BTN_401", "<ButtonRelease-1>",
                                                          lambda event, tag="BTN_401": self.game_click(event, tag))
                                self.game_canvas.create_image(
                                    self.section_col1_w - math.floor(self.section_toolbar_h) * 13 + 4 + math.floor(self.section_toolbar_h) / 2,
                                    self.section_toolbar_y - 16,
                                    image=self.img_c_over[12],
                                    activeimage=self.img_c_over[13],
                                    anchor=SW,
                                    tags=("BTN_402", "popup", "toclick", "choose")
                                )
                                self.game_canvas.tag_bind("BTN_402", "<ButtonRelease-1>",
                                                          lambda event, tag="BTN_402": self.game_click(event, tag))
                        else:
                            self.txt_status[1] = "Wissen teilen nicht möglich."

                    if self.TP.turns['sender'] == "choose":
                        print(">>> X >>> 4 choose", self.TP.turns)
                        self.game_canvas.delete("choose")
                        if self.TP.turns['choose'] == 401:
                            # player is sender
                            self.TP.set_exchange('s', self.TP.num)
                            self.txt_status[1] = "Wähle Karte zum geben aus."
                            self.draw_card_highlight(self.city2card(self.check_exchange("send_cards")), "G")
                        elif self.TP.turns['choose'] == 402:
                            # player is receiver
                            self.TP.set_exchange('r', self.TP.num)
                            self.txt_status[1] = "Wähle Platz für neue Karte aus."
                            self.draw_card_highlight(0, 0, "select_space")

                    if self.TP.turns['sender'] == "CARD":
                        print(">>> X >>> 4 CARD", self.TP.turns)
                        # reset overlay
                        self.draw_card_highlight(None)

                        if self.TP.exchange['s'] == self.TP.num:
                            # player is sender, set card to send
                            print(">>> X >>>", self.TP.turns['card'])
                            print(">>> X >>>", self.TP.exchange)
                            self.TP.set_exchange('c', self.TP.cards[self.TP.turns['card']])
                            # draw selection
                            self.draw_player_selection(self.check_exchange("receiver"))
                            self.txt_status[1] = "Wähle den Empfänger aus."  # select receiver ... -> player is sender
                        elif self.TP.exchange['r'] == self.TP.num:
                            # player is receiver, set card to burn (optional)
                            if self.TP.turns['card'] < len(self.TP.cards):
                                self.TP.set_exchange('b', self.TP.cards[self.TP.turns['card']])
                            # draw selection
                            self.draw_player_selection(self.check_exchange("sender"))
                            self.txt_status[1] = "Wähle Kartengeber aus."  # select sender ....... -> player is receiver

                    if self.TP.turns['sender'] == "PLAY":
                        print(">>> X >>> 4 PLAY", self.TP.exchange)
                        # reset overlay
                        self.draw_player_selection()

                        if self.TP.exchange['s'] == self.TP.num:
                            # player is sender, set receiver
                            self.TP.set_exchange('r', self.TP.turns['player'])
                        elif self.TP.exchange['r'] == self.TP.num:
                            # player is receiver, set sender
                            self.TP.set_exchange('s', self.TP.turns['player'])

                        # execute
                        # self.xchng = {'status': "", 'sender': 0, 'card': 0, 'receiver': 0}
                        self.txt_status[1] = "Warte auf anderen Spieler"
                        self.TP.set_exchange('status', "request")
                        print(">>> X >>> Warte auf anderen Spieler", self.TP.exchange)

                        self.value = {'v': self.localversion,
                                      'exchange': self.TP.exchange}
                        self._update('card_exchange')
                        # update game
                        # self.TP.cs_reset()
                        # self.draw_card_highlight(None)
                        # self.game_canvas.delete("popup")
                # endregion
                # region ---  5 - healing ---------------------------------------------------------------------------- #
                if self.TP.turns['turn'] == 5:
                    if self.TP.turns['sender'] == "BTN":
                        if self.city[self.TP.pos].get("c"):
                            self.TP.cs_reset()
                            check = [0, 0, 0, 0]
                            for c in self.TP.cards:
                                if c <= 47:
                                    check[self.city[c].get("d")] += 1
                            for idf, f in enumerate(check):
                                if f > 4 or (self.TP.role == 1 and f > 3):
                                    if self.healing[idf] == 0:
                                        selection = []
                                        for idc, c in enumerate(self.TP.cards):
                                            if c <= 47:
                                                if self.city[c].get("d") == idf:
                                                    selection.append(idc)
                                        if self.TP.role == 1:
                                            self.txt_status[1] = "Wähle 4 Karten aus."
                                        else:
                                            self.txt_status[1] = "Wähle 5 Karten aus."
                                        self.draw_card_highlight(selection, "G")
                                        break
                                    else:
                                        self.txt_status[1] = "Heilmittel bereits erforscht"
                                else:
                                    self.txt_status[1] = "Nicht genug Karten von einer Farbe"
                        else:
                            self.txt_status[1] = "Forschungscenter benötigt"
                    if self.TP.turns['sender'] == "CARD":
                        c_num = self.TP.turns['card']
                        if c_num in self.TP.card_selection:
                            self.TP.cs_remove(c_num)
                            self.draw_card_highlight([c_num], "G", "card_highlight_sel")
                        else:
                            self.TP.cs_append(c_num)
                            self.draw_card_highlight([c_num], "H", "card_highlight_sel")

                        required = 4 if self.TP.role == 1 else 5

                        if len(self.TP.card_selection) < required:
                            self.txt_status[1] = str(len(self.TP.card_selection)) + "/" + \
                                              str(required) + " Karten ausgewählt"
                        else:
                            # update game
                            self.txt_status[1] = "Heilmittel entdeckt."
                            # update server
                            remove_cards = []
                            for c in self.TP.card_selection:
                                remove_cards.append(self.TP.cards[c])
                            self.value = {'v': self.localversion,
                                          'player': self.TP.num,
                                          'cards': remove_cards}
                            self.TP.cs_reset()
                            self._update('heal')
                # endregion
                # region ---  7 - krisenmanager only ----------------------------------------------------------------- #
                if self.TP.turns['turn'] == 7:
                    if self.TP.turns['sender'] == "BTN":
                        if self.special_val["r3"] == 0:
                            self.value = {'v': self.localversion,
                                          'turn': "request",
                                          'player': self.TP.num}
                            self._update('role3')
                        else:
                            self.txt_status[1] = "Nur eine Karte möglich"

                    if self.TP.turns['sender'] == "response":
                        if len(self.TP.turns['card']) > 0:
                            self.TP.cs_reset()
                            self.txt_status[1] = "Wähle Karte aus"
                            self.draw_cards(self.TP.turns['card'], 8)
                        else:
                            self.txt_status[1] = "Keine Ereigniskarte im Ablagestapel"

                    if self.TP.turns['sender'] == "CARD":
                        # update game
                        self.game_canvas.delete("popup")
                        self.dismiss_tooltip()
                        self.txt_status[1] = ""
                        # update server
                        self.value = {'v': self.localversion,
                                      'turn': "getcard",
                                      'card': self.TP.turns['card'],
                                      'player': self.TP.num}
                        self._update('role3')
                # endregion
                # region ---  8 - move ------------------------------------------------------------------------------- #
                if self.TP.turns['turn'] == 8:
                    if self.TP.turns['sender'] == "BTN":  # initialize action
                        self.get_player_path()
                        self.draw_city_highlight(self.TP.range)
                        self.txt_status[1] = "Bewegen: Wähle Ziel. (keine Karte notwendig)"
                    if self.TP.turns['sender'] == "CITY":  # do action
                        self.draw_city_highlight()
                        self.txt_status[1] = ""
                        move_player = self.logistician if self.logistician < 3 else self.TP.num
                        self.draw_toolbar("update")
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.TP.num,
                                      'path': self.get_player_path(self.TP.turns['city']),
                                      'moveplayer': move_player,
                                      'moveto': self.TP.turns['city'],
                                      'steps': self.TP.turns['steps'],
                                      'usedcards': []}
                        # reset other player movement by logistican
                        self.game_canvas.delete("MOP")
                        self.logistician = 5
                        self._update('player_move')
                # endregion
                # region ---  9 - fly direct ------------------------------------------------------------------------- #
                if self.TP.turns['turn'] == 9:
                    if self.TP.turns['sender'] == "BTN":  # initialize action
                        self.draw_city_highlight(self.TP.cards)
                        self.txt_status[1] = "Direktflug: Wähle Ziel. (eine Karte wird benötigt)"
                    if self.TP.turns['sender'] == "CITY":  # do action
                        self.draw_city_highlight()
                        self.txt_status[1] = ""
                        move_player = self.logistician if self.logistician < 3 else self.TP.num
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.TP.num,
                                      'moveplayer': move_player,
                                      'moveto': self.TP.turns['city'],
                                      'steps': 1,
                                      'usedcards': [self.TP.turns['city']]}
                        # reset other player movement by logistican
                        self.game_canvas.delete("MOP")
                        self.logistician = 5
                        self._update('player_move')
                # endregion
                # region --- 10 - fly charter ------------------------------------------------------------------------ #
                if self.TP.turns['turn'] == 10:
                    if self.TP.turns['sender'] == "BTN":  # initialize action
                        pos = self.all_player_pos[self.logistician] if self.logistician < 3 else self.TP.pos
                        if pos in self.TP.cards:
                            self.txt_status[1] = "Charterflug: Wähle Zielstadt."
                            allcitys = [x for x in range(48)]
                            allcitys.remove(pos)
                            self.draw_city_highlight(allcitys)
                        else:
                            self.draw_city_highlight()
                            self.txt_status[1] = "Charterflug nicht möglich. (Karte vom Standort wird benötigt)"
                    if self.TP.turns['sender'] == "CITY":  # do action
                        self.draw_city_highlight()
                        self.txt_status[1] = ""
                        move_player = self.logistician if self.logistician < 3 else self.TP.num
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.TP.num,
                                      'moveplayer': move_player,
                                      'moveto': self.TP.turns['city'],
                                      'steps': 1,
                                      'usedcards': [self.all_player_pos[move_player]]}
                        # reset other player movement by logistican
                        self.game_canvas.delete("MOP")
                        self.logistician = 5
                        self._update('player_move')
                # endregion
                # region --- 11 - fly special ------------------------------------------------------------------------ #
                if self.TP.turns['turn'] == 11:
                    if self.TP.turns['sender'] == "BTN":  # initialize action
                        pos = self.all_player_pos[self.logistician] if self.logistician < 3 else self.TP.pos
                        if self.city[pos]['c']:
                            self.txt_status[1] = "Sonderflug: Wähle Zielstadt mit Forschungscenter."
                            citys = []
                            for c in self.city:
                                if c['c']:
                                    citys.append(c['ID'])
                            citys.remove(pos)
                            self.draw_city_highlight(citys)
                        else:
                            self.draw_city_highlight()
                            self.txt_status[1] = "Sonderflug nicht möglich. (Forschungszentrum benötigt)"
                    if self.TP.turns['sender'] == "CITY":  # do action
                        self.draw_city_highlight()
                        self.txt_status[1] = ""
                        move_player = self.logistician if self.logistician < 3 else self.TP.num
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.TP.num,
                                      'moveplayer': move_player,
                                      'moveto': self.TP.turns['city'],
                                      'steps': 1,
                                      'usedcards': []}
                        # reset other player movement by logistican
                        self.game_canvas.delete("MOP")
                        self.logistician = 5
                        self._update('player_move')
                # endregion
                # region --- 12 - LOGISTIKER - select player --------------------------------------------------------- #
                if self.TP.turns['turn'] == 12:
                    if self.TP.turns['sender'] == "BTN":  # initialize action
                        self.draw_city_highlight()

                        if self.logistician > 3:
                            self.logistician = self.TP.num

                        if self.logistician == self.TP.num:  # switch to other player
                            selected_player = []
                            for num, name in enumerate(self.all_player_name):
                                if name != '':
                                    selected_player.append(num)
                            self.draw_player_selection(selected_player, "LOG1")
                            self.txt_status[1] = "Wähle zu bewegenden Spieler"
                        else:  # switch back to player
                            self.logistician = self.TP.num
                            self.txt_status[1] = "Du bewegst dich wieder selber"
                            self.game_canvas.delete("MOP")
                            self.draw_toolbar("update")

                    if self.TP.turns['sender'] == "PLAY":  # get player
                        self.game_canvas.delete("popup")
                        self.logistician = self.TP.turns['player']
                        self.txt_status[1] = "Du bewegst: " + self.all_player_name[self.logistician]

                        self.game_canvas.create_line(
                            self.section_col1_w - math.floor(self.section_toolbar_h) * (17 - 8) - 1,
                            self.section_toolbar_y - 2,
                            self.section_col1_w - math.floor(self.section_toolbar_h) * (17 - 13),
                            self.section_toolbar_y - 2,
                            fill=get_role_color(self.all_player_role[self.logistician]),
                            width=3,
                            tags="MOP"
                        )
                        self.game_canvas.create_image(
                            self.section_col1_w - math.floor(self.section_toolbar_h) * (17 - 8) - 1,
                            self.section_toolbar_y - 3,
                            image=self.img_p[self.all_player_role[self.logistician] - 1],
                            anchor=SW,
                            tags="MOP"
                        )
                        self.draw_toolbar("update")
                # endregion
                # region --- 17 - BETRIEBSEXPERTE - fly from center -------------------------------------------------- #
                if self.TP.turns['turn'] == 17:
                    if self.TP.turns['sender'] == "BTN":  # initialize action
                        if self.special_val['r7']:
                            if self.city[self.TP.pos]['c']:
                                ccard = False
                                for c in self.TP.cards:
                                    if c < 48:
                                        ccard = True
                                        self.draw_card_highlight([self.TP.cards.index(c)], "G")
                                if ccard:
                                    self.txt_status[1] = "Sonderflug: Wähle Karte zum abwerfen."

                                else:
                                    self.txt_status[1] = "Sonderflug nicht möglich. (Eine Stadtkarte wird benötigt)"

                            else:
                                self.draw_city_highlight()
                                self.txt_status[1] = "Sonderflug nicht möglich. (Forschungszentrum benötigt)"
                        else:
                            self.txt_status[1] = "Fähigkeit nur einmal pro Runde möglich"

                    if self.TP.turns['sender'] == "CARD":
                        self.draw_card_highlight()
                        self.txt_status[1] = "Sonderflug: Wähle Resieziel aus."
                        allcitys = [x for x in range(48)]
                        allcitys.remove(self.TP.pos)
                        self.draw_city_highlight(allcitys)

                    if self.TP.turns['sender'] == "CITY":
                        self.draw_city_highlight()
                        self.special_val['r7'] = False  # Block turn for this round
                        self.txt_status[1] = ""
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.TP.num,
                                      'moveplayer': self.TP.num,
                                      'moveto': self.TP.turns['city'],
                                      'steps': 1,
                                      'usedcards': [self.TP.cards[self.TP.turns['card']]]}
                        self._update('player_move')
                # endregion
                # region --- 13 - LOGISTIKER - move player to player ------------------------------------------------- #
                if self.TP.turns['turn'] == 13:
                    if self.TP.turns['sender'] == "BTN":  # initialize action
                        self.draw_city_highlight()
                        selected_player = []
                        for num, name in enumerate(self.all_player_name):
                            if name != '':
                                selected_player.append(num)
                        self.draw_player_selection(selected_player, "LOG2")
                        self.txt_status[1] = "Wähle zu bewegenden Spieler"

                    if self.TP.turns['sender'] == "PLAY":  # get player
                        self.game_canvas.delete("popup")

                        selected_city = []
                        for num, name in enumerate(self.all_player_name):
                            if name != '':
                                selected_city.append(self.all_player_pos[num])
                        selected_city.remove(self.all_player_pos[self.TP.turns['player']])

                        self.draw_city_highlight(selected_city)
                        self.txt_status[1] = "Spezialfähigkeit: Wähle Zielstadt"

                    if self.TP.turns['sender'] == "CITY":  # get city and execute
                        self.draw_city_highlight()
                        self.txt_status[1] = ""
                        self.logistician = 5
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.TP.num,
                                      'moveplayer': self.TP.turns['player'],
                                      'moveto': self.TP.turns['city'],
                                      'steps': 1,
                                      'usedcards': []}
                        self._update('player_move')
                # endregion

                # --- 32 - end turn ---------------------------------------------------------------------------------- #
                if self.TP.turns['turn'] == 16 and self.TP.turns['sender'] == "BTN":
                    self.TP.set_turns('turn', 0)
                    self.txt_status[1] = "Beende Zug"
                    # update server
                    self.value = {'v': self.localversion}
                    self._update('end_turn')
                # endregion
            else:  # ACTION is over start next STATE
                # remove all highlights
                if not self.TP.turns['secondcity']:
                    self.draw_city_highlight()
                self.game_canvas.delete("popup")
                self.txt_status[1] = "Zug beenden."
                self.txt_status[0] = ""
                self.TP.set_turns("turn", 999)
                self.game_STATE = "SUPPLY"
                self.draw_toolbar("update")

        if self.game_STATE == "SUPPLY" or self.game_STATE == "EPIDEMIE":
            # awaits click on cards, execute supply or epidemie, STATE ends when draw_cards = 0
            if len(self.TP.drawcards) > 0:
                # region ###### set statustext ######
                if self.TP.drawcards[0] != self.card_epidemie:
                    if len(self.TP.drawcards) > 1:
                        self.txt_status[0] = "Nachschubphase: 2 Karten ziehen"
                    else:
                        self.txt_status[0] = "Nachschubphase: 1 Karten ziehen"
                    if self.game_STATE == "EPIDEMIE":
                        self.txt_status[0] = "Epidemieausbruch."
                else:
                    self.txt_status[0] = "Epidemie auslösen."
                # endregion
                # region ###### actions ######
                # --- drawcard --------------------------------------------------------------------------------------- #
                if self.TP.drawcards[0] != self.card_epidemie and self.game_STATE != "EPIDEMIE":
                    if self.TP.turns['sender'] == "CARD":

                        playercard_add = []
                        playercard_remove = []
                        playercard_switch = []
                        playercard_burn = []
                        if 7 > self.TP.turns['card'] >= len(self.TP.cards):  # add card to player
                            playercard_add.append(self.TP.drawcards[0])
                        elif self.TP.turns['card'] == 7:  # dismiss card
                            playercard_burn.append(self.TP.drawcards[0])
                        else:  # replace card
                            playercard_switch.append((self.TP.cards[self.TP.turns['card']],
                                                      self.TP.drawcards[0]))

                        self.TP.dc_del(0)
                        self.gameupdatelist['cards'].append(7)

                        # update server
                        self.value = {'player': self.TP.num,
                                      'add': playercard_add,
                                      'remove': playercard_remove,
                                      'switch': playercard_switch,
                                      'burn': playercard_burn}

                        self._update('update_cards')
                # --- epidemie --------------------------------------------------------------------------------------- #
                else:
                    # start epidemie and draw infection card
                    if self.game_STATE == "SUPPLY" and self.TP.turns['sender'] == "CARD":
                        _print("[" + str(self.TP.num) + "]",
                               ">>> EPIDEMIE >>>",
                               str(self.TP.drawcards))
                        self.game_canvas.itemconfigure(self.i_quicktip, fill="")
                        self.txt_status[1] = ""
                        self.game_STATE = "EPIDEMIE"
                        self.TP.dc_del(0)
                        self.TP.set_turns('sender', "")
                        self._update('draw_epidemiecard')
                    # infect city
                    if self.game_STATE == "EPIDEMIE" and self.TP.turns['sender'] == "CARD":
                        inf_card = self.TP.drawcards[0]
                        self.TP.dc_del(0)
                        self.gameupdatelist['cards'].append(7)
                        self.game_STATE = "SUPPLY"
                        # update server -> do calculation online
                        self.value = {'v': self.localversion,
                                      'card': inf_card,
                                      'epidemie': True}
                        self._update('update_inf')
                # endregion
            else:
                if self.TP.turns["turn"] == 999:
                    # INIT SUPPLY with drawing cards
                    self.TP.set_turns("turn", 0)
                    self.TP.set_turns('sender', "")
                    self.txt_status[1] = ""
                    self._update('draw_playercard')
                else:
                    if self.TP.turns['sender'] == "BTN" \
                            and self.TP.turns['turn'] == 16:
                        self.game_canvas.itemconfigure(self.i_quicktip, fill="")
                        self.game_canvas.delete("popup")
                        self.game_canvas.delete("abg")
                        self.TP.set_turns("turn", 999)
                        self.game_STATE = "INFECT"
                    else:
                        # SUPPLY is over start next STATE
                        self.txt_status[1] = "Beende deinen Zug"
                        self.txt_status[0] = ""
                        self.draw_toolbar("update")

        if self.game_STATE == "INFECT":
            # awaits click on cards, execute supply, STATE ends when draw_cards = 0
            if len(self.TP.drawcards) > 0:
                # region ###### set statustext ######
                self.txt_status[1] = "Infiziere Stadt"
                # endregion
                # region ###### actions ######
                if self.TP.turns['sender'] == "CARD":
                    inf_card = self.TP.drawcards[0]
                    self.TP.dc_del(0)
                    self.gameupdatelist['cards'].append(7)

                    # update server -> do calculation online
                    self.value = {'v': self.localversion,
                                  'card': inf_card}
                    self._update('update_inf')
                # endregion
            else:
                # INIT INFECT with drawing cards
                if self.TP.turns["turn"] == 999:
                    self.TP.set_turns("turn", 0)
                    self._update('draw_infcard')
                # INFECT is over start next STATE -> next player
                else:
                    self.txt_status[1] = ""
                    self.txt_status[0] = ""
                    self.game_canvas.itemconfigure(self.i_quicktip, fill="")
                    self.game_STATE = "PASSIV"
                    self.value = {'v': self.localversion,
                                  'player_num': self.TP.num}
                    self._update('turn_over')
        # endregion

        # --- reset sender ----------------------------------------------------------------------------------- #
        self.TP.set_turns('sender', "")
        # update game if necessary
        if self.game_STATE != 'INIT' and self.game_STATE != 'WAIT':
            self.game_show()

    def game_update(self, args):
        _print(">>> ", args)

        # city
        if 'C' in args:
            for c in args['C']:
                num = int(c)
                akt_c = self.city[num]['i'], self.city[num]['c']
                if akt_c != ([args.get("C")[c][0], args.get("C")[c][1], args.get("C")[c][2], args.get("C")[c][3]],
                             args.get("C")[c][4]):
                    self.city[num]['i'][0] = args.get("C")[c][0]
                    self.city[num]['i'][1] = args.get("C")[c][1]
                    self.city[num]['i'][2] = args.get("C")[c][2]
                    self.city[num]['i'][3] = args.get("C")[c][3]
                    self.city[num]['c'] = args.get("C")[c][4]
                    self.gameupdatelist['city'].append(num)

        # cards
        if 'CP' in args:
            self.all_player_cards = args.get("CP")
            cards = self.all_player_cards[self.TP.num]
            if self.TP.cards != cards:
                r = len(self.TP.cards) if len(self.TP.cards) < len(cards) \
                    else len(cards)
                for c in range(0, 7):
                    if c < r:
                        if self.TP.cards[c] != cards[c]:
                            self.gameupdatelist['cards'].append(c)
                    else:
                        self.gameupdatelist['cards'].append(c)
                self.TP.set_cards(self.all_player_cards)
            self.gameupdatelist['sidebar'].append('CP')

        # special val
        if 'C3' in args:
            if self.special_val['r3'] != args.get("C3")['r3']:
                self.special_val['r3'] = args.get("C3")['r3']
                self.gameupdatelist['cards'].append(9)
            if self.special_val['a50'] != args.get("C3")['a50']:
                self.special_val['a50'] = args.get("C3")['a50']
                for num in self.special_val['a50']:
                    self.gameupdatelist['city'].append(num)

        # stats
        if 'SO' in args:
            if self.outbreak != args['SO']:
                self.outbreak = args['SO']
                self.gameupdatelist['sidebar'].append('SO')
        if 'SL' in args:
            if self.inflvl != args['SL']:
                self.inflvl = args['SL']
                self.gameupdatelist['sidebar'].append('SL')
        if 'SS' in args:  # state supply
            if self.supplies != args['SS']:
                self.supplies = args['SS']
                self.gameupdatelist['sidebar'].append('SS')
                # print("VISUAL, supply")
        if 'SI' in args:
            if self.infection != args['SI']:
                self.infection = args['SI']
                self.gameupdatelist['sidebar'].append('SI')
        if 'SH' in args:
            if self.healing != args['SH']:
                self.healing = args['SH']
                self.gameupdatelist['sidebar'].append('SH')

        # player
        if 'PP' in args:
            if self.all_player_pos != args['PP']:
                self.all_player_pos = args['PP']
                self.TP.set_pos(self.all_player_pos)
                self.gameupdatelist['playerpos'] = 1
        if 'PC' in args:
            self.current_player = args['PC'][0]
            self.TP.set_turns('LEFT', args['PC'][1])
            self.gameupdatelist['sidebar'].append('PC')

        # exchange parameter
        if 'CE' in args:
            if self.TP.exchange != args.get("CE"):
                self.TP.exchange = args.get("CE")
                self.gameupdatelist['exchange'] = 1

        # visual turns
        if 'VI' in args:
            if self.visual != args.get('VI'):
                self.visual = args.get('VI')
                self.gameupdatelist['visual'] = 1

        # status
        if 'S' in args:
            if args['S']['s'] == "LOSE_GAME":
                self.game_lose(args['S']['r'])
            if args['S']['s'] == "WIN_GAME":
                self.game_win()

        # TODO check, remove or delete dublicate
        # newupdate['S'] = {'s': self.game_STATE, 'r': self.reason}
        # newupdate['PN'] = self.player_name
        # newupdate['PR'] = self.player_role
        # newupdate['PS'] = self.player_rdy

        # update version
        self.localversion = args.get("v")

        return 'getVersion'

    def game_click(self, event, *args):

        def confirm(card):
            oldimage = self.game_canvas.itemcget(card, "activeimage")
            self.game_canvas.itemconfig(card, activeimage=self.img_c_over[16])
            time.sleep(3)
            self.game_canvas.itemconfig(card, activeimage=oldimage)

        if not self.block_request:
            # region ###### CLICK @ CARDS ##############################################################################
            if 8 < event.y < self.section_card_h:  # cardsection
                card_num = math.floor(float(event.x) / (self.section_col1_w / 8))
                _print("[" + str(self.TP.num) + "]",
                       "CLICKED at Card: " + str(card_num))

                conf = False
                getcard = (next((s for s in self.game_canvas.gettags(tk.CURRENT) if "conf" in s), None))
                if getcard is not None:
                    if str(self.game_canvas.itemcget(getcard, "activeimage")) == str(self.img_c_over[16]):
                        conf = True
                    else:
                        threading.Thread(target=confirm, args=(getcard,)).start()
                else:
                    conf = True

                if conf:
                    self.TP.set_turns('sender', "CARD")
                    self.TP.set_turns('card', card_num)

                self.dismiss_tooltip()
            # endregion
            # region ###### CLICK @ FIELD ##############################################################################
            elif self.section_field_y < event.y < self.section_field_y + self.section_field_h:  # map -> find city

                sender = str(args[0][:4])

                if sender == "CITY":  # clicked on city
                    mycitynum = int(args[0][4:])
                    # mycity = self.city[mycitynum].get("name")
                    self.TP.set_turns('city', mycitynum)
                    self.TP.set_turns('steps', len(self.get_player_path(mycitynum)))

                if sender == "DIS_":  # clicked on disease-selection
                    self.TP.set_turns('disease', int(args[0][4:]))

                if sender == "PLAY":  # clicked on player-selection
                    self.TP.set_turns('player', int(args[0][4:]))

                if sender == "BTN_":  # clicked on in-game-btn (actioncard)
                    if int(args[0][4:]) == 48:
                        sender = "exec48"
                    if int(args[0][4:]) == 481:
                        sender = "cancel48"
                    if int(args[0][4:]) == 401:
                        sender = "choose"
                        self.TP.set_turns('choose', 401)
                    if int(args[0][4:]) == 402:
                        sender = "choose"
                        self.TP.set_turns('choose', 402)

                if sender == "CARD":  # clicked on card on canvas
                    self.TP.set_turns('card', int(args[0][4:]))

                _print("[" + str(self.TP.num) + "]",
                       "CLICKED at Field: Sender[" + str(sender) + "], value[" + str(args[0][4:]) + "]")

                self.TP.set_turns('sender', sender)
            # endregion
            # region ###### CLICK @ BAR/BTN ############################################################################
            elif event.y > self.section_toolbar_y:
                posx = self.game_canvas.coords(tk.CURRENT)[0] + event.widget.winfo_width() / 34
                num = math.floor(float(posx) / self.section_col1_w * 17)

                # 2 functions on one button
                if num == 12 and self.TP.role != 5:
                    num = 17

                _print("[" + str(self.TP.num) + "]",
                       "CLICKED at BTN: " + str(num))

                # remove existing highlights
                # TODO reduce remove options
                self.draw_card_highlight(None)
                self.draw_card_highlight()
                self.draw_city_highlight()

                self.game_canvas.delete("popup")
                self.txt_status[1] = ""

                if (self.TP.turns['LEFT'] > 0 and self.game_STATE == "ACTION") \
                        or num in [6, 15, 16]:
                    self.TP.set_turns('turn', num)
                    self.TP.set_turns('sender', "BTN")
                else:
                    if self.TP.turns['LEFT'] <= 0:
                        self.txt_status[1] = "keine Züge vorhanden"
                    else:
                        self.txt_status[1] = "Du bist nicht am Zug."
            # endregion

            self._update()

    def game_show(self):

        # region ###### get actual window dimension and calculate aspect-ration ######
        self.update()
        win_w = self.winfo_width()
        win_h = self.winfo_height()

        # units:
        ux = 44             # new dimensions  44:25
        uy = 25
        uy_card = 6         # cards:    34: 6
        uy_status = 1       # status:   34: 1
        uy_field = 16       # field:    34:16
        uy_toolbar = 2      # toolbar:  34: 2
        ux_side = 10        # side: 10:25

        # calculate maximum size within aspect ratio
        h = win_w / ux * uy
        w = win_h / uy * ux

        if h > win_h:
            area_w = w
            area_h = win_h
        else:
            area_w = win_w
            area_h = h

        self.section_col1_w = area_w / ux * (ux - ux_side)
        self.section_card_h = (area_h / uy * uy_card)
        self.section_status_y = (area_h / uy * uy_card)
        self.section_status_h = (area_h / uy * uy_status)
        self.section_field_y = (area_h / uy * (uy_card + uy_status))
        self.section_field_h = (area_h / uy * uy_field)
        self.section_toolbar_y = (area_h / uy * (uy_card + uy_status + uy_field))
        self.section_toolbar_h = area_h - self.section_toolbar_y

        self.section_side_x = self.section_col1_w + 3
        self.section_side_w = area_h / uy * ux_side
        self.section_side_h = area_h
        self.section_side_row_h = area_h / uy

        s_inf = 320 * self.section_col1_w / (3380 * 2)  # variable for marker size (half the size)
        s_cen = s_inf * 120 / 320
        # endregion

        if self.old_window_h != win_h or self.old_window_w != win_w or self.reload:
            # resize #########################################
            self.reload = False
            _print("RESIZE WINDOW")
            # destroy all
            for child in self.winfo_children():
                child.destroy()

            # set base frame over whole window
            self.game_frame = Frame(self, width=win_w, height=win_h, bg="#222", highlightthickness=0)
            self.game_frame.place(relx=0.5, rely=0.5, width=win_w, height=win_h, anchor=CENTER)

            # canvas -> area to draw on with correct aspect ratio
            self.game_canvas = ResizingCanvas(self.game_frame, width=area_w, height=area_h,
                                              bg="#333", highlightthickness=0)
            self.game_canvas.place(relx=.5, rely=.5, anchor="c")

            # BG toolbar/statusbar
            self.game_canvas.create_rectangle(
                am_rect(0, self.section_toolbar_y + 3, self.section_col1_w, self.section_toolbar_h - 6),
                fill="#282828", outline='#3a3a3a')
            self.game_canvas.create_rectangle(am_rect(2, self.section_status_y + 2,
                                                      self.section_col1_w - 4, self.section_status_h - 4),
                                              fill="#747474",
                                              outline='#222')

            # infotext
            fs = int((self.section_status_h - 6.6475) / 1.4951)   # calculate font size
            if fs > 16:
                fs = int((fs - 16) / 4 + 16)

            self.i_status = self.game_canvas.create_text(
                int(self.section_col1_w / 2), int(self.section_status_y + self.section_status_h / 2),
                text=(self.txt_status[0] + " | " + self.txt_status[1]),
                fill="#000000",
                anchor=CENTER,
                font=('Helvetica', fs))

            # map
            self.img_map = ImageTk.PhotoImage(
                self.img_map_raw.resize((int(self.section_col1_w), int(self.section_field_h)), Image.ANTIALIAS))
            self.game_canvas.create_image(0, self.section_field_y, image=self.img_map, anchor=NW)
            # field overlay (city names)
            self.img_overlay_game = ImageTk.PhotoImage(
                self.img_overlay_game_raw.resize((int(self.section_col1_w), int(self.section_col1_w / 2.125)),
                                                 Image.ANTIALIAS))
            self.game_canvas.create_image(0, self.section_field_y,
                                          image=self.img_overlay_game, anchor=NW, tags="game_overlay")

            # region Prepare Elements ----------------------------------------------------------------------------------

            # prepare cards/BG and overlay
            for bg in range(0, 8):  # gamecard overlay
                self.game_canvas.create_rectangle(self.carddim("bg", bg), fill="#282828")
            for o in range(0, 8):
                self.img_c_over[o] = ImageTk.PhotoImage(self.img_c_over_raw[o].
                        resize(self.carddim("high_size"),
                               Image.ANTIALIAS))
            self.img_c_over[16] = ImageTk.PhotoImage(self.img_c_over_raw[16].
                                                    resize(self.carddim("high_size"),
                                                           Image.ANTIALIAS))
            for o in range(8, 10):  # card 3 extra overlay
                self.img_c_over[o] = ImageTk.PhotoImage(self.img_c_over_raw[o].
                                                        resize([int(self.carddim("high_size")[0] / 2),
                                                           int(self.carddim("high_size")[1] / 2)],
                                                           Image.ANTIALIAS))
            for o in range(10, 16):  # share knowledge buttons
                self.img_c_over[o] = ImageTk.PhotoImage(self.img_c_over_raw[o].
                    resize((int(self.section_toolbar_h)*2, int(self.section_toolbar_h)*2),
                           Image.ANTIALIAS))

            # prepare overlay sidebar
            self.img_side = ImageTk.PhotoImage(
                self.img_side_raw.resize((int(self.section_side_w), int(self.section_side_h)),
                                             Image.ANTIALIAS))
            self.game_canvas.create_image(self.section_side_x, 0,
                                              image=self.img_side, anchor=NW,
                                              tags="side_overlay")

            # prepare infection graphics: scale
            for x in range(0, 4):
                for y in range(0, 4):
                    for z in range(0, 3):
                        self.img_inf[z][y][x] = ImageTk.PhotoImage(self.img_inf_raw[x][y]
                                                                   .resize((int(s_inf), int(s_inf)), Image.ANTIALIAS)
                                                                   .rotate(z * 120 + 120))
            # prepare center 120x120
            self.img_center = ImageTk.PhotoImage(self.img_center_raw.resize((int(s_cen), int(s_cen)), Image.ANTIALIAS))

            # prepare zaeh indicator
            self.img_zaeh = ImageTk.PhotoImage(self.img_zaeh_raw.resize((int(s_inf), int(s_inf)), Image.ANTIALIAS))

            # prepare additional icons
            for num in range(0, 23):
                for s in range(0, 3):
                    self.img_icon[s][num] = ImageTk.PhotoImage(self.img_icon_raw[s][num].
                        resize((int(self.section_toolbar_h), int(self.section_toolbar_h)),
                               Image.ANTIALIAS))

            # prepare player card and name
            card_part_w = (self.section_col1_w - 6) / 8
            self.img_char[self.TP.role] = \
                ImageTk.PhotoImage(self.img_char_raw[self.TP.role]
                                   .resize((int(card_part_w/2), int(card_part_w/7*10/2)), Image.ANTIALIAS))

            # updatelist
            self.gameupdatelist = {'city': [0], 'cards': [9],
                                   'playerpos': 0, 'sidebar': ["CP", "PC", "SO", "SL", "SS", "SH", "SI"], 'exchange': 1,
                                   'visual': 0}
            # cities
            for c in range(1, 48):  # loop through citys
                self.gameupdatelist['city'].append(c)

            # cards
            for c in range(0, len(self.TP.cards)):
                self.gameupdatelist['cards'].append(c)

            # endregion

            # region DRAW ----------------------------------------------------------------------------------------------
            self.draw_player()
            self.draw_toolbar()
            self.draw_sidebar()

            # player name and card
            x = 6
            y = int(self.section_field_y + self.section_field_h - 6)
            t = self.game_canvas.create_text(x, y,
                                             text=self.TP.name,
                                             fill="#ffffff",
                                             anchor=SW,
                                             font=('Helvetica', 10, 'bold'))
            self.game_canvas.create_image(x, y - (self.game_canvas.bbox(t)[3] - self.game_canvas.bbox(t)[1]) - 2,
                                          image=self.img_char[self.TP.role],
                                          anchor=SW,
                                          tags='thisplayerrole')
            self.special_val['pos'] = (int(6 + card_part_w / 2 + 4),
                                       y - (self.game_canvas.bbox(t)[3] - self.game_canvas.bbox(t)[1]) - 2)

            self.game_canvas.tag_bind("thisplayerrole", "<Enter>", self.draw_tooltip_player)
            self.game_canvas.tag_bind("thisplayerrole", "<Leave>", self.dismiss_tooltip)

            # quicktips
            self.i_quicktip = self.game_canvas.create_text(0, 0, text="", fill="", anchor=S,
                                                           font=('Helvetica', 10), tags="info")
            # endregion

            # set variables for resize-check
            self.old_window_w = win_w
            self.old_window_h = win_h

        # update elements
        self.draw_toolbar("update")

        # region redraw elements from updatelist
        for c in self.gameupdatelist['city']:
            self.draw_cities(c)
        for c in self.gameupdatelist['cards']:
            self.draw_cards(c, 0)

        if self.gameupdatelist['playerpos'] == 1:
            self.draw_player()

        # generate statusline
        line = self.txt_status[0]
        if self.txt_status[1] != "":
            if self.txt_status[0] != "":
                line = line + " | "
            line = line + self.txt_status[1]
        if self.game_canvas.itemcget(self.i_status, 'text') != line:
            self.game_canvas.itemconfigure(self.i_status, text=line)

        if len(self.gameupdatelist['sidebar']) > 0:
            self.draw_sidebar()

        if self.gameupdatelist['visual']:
            self.draw_visual()

        if self.gameupdatelist['exchange']:
            self.exchange_card()
        # endregion

        order = ()
        for layer in ["info", "toclick", "player", "thisplayerrole", "side_overlay", "game_overlay"]:
            order = order + (layer,)
            self.game_canvas.tag_raise(order)
        # i_quicktip

    # region ------ MAINGAME -------------------------------------------------------------------------------------------
    def game_lose(self, reason):
        self.game_STATE = "LOSE_GAME"
        self.config(cursor="pirate")
        _print("[" + str(self.TP.num) + "]",
               "> You lose.")

        s = int(self.winfo_height() * 0.66)

        self.img_lose = ImageTk.PhotoImage(self.img_lose_raw.resize((s, s), Image.ANTIALIAS))
        lose = self.game_canvas.create_image(
            int(self.section_col1_w / 2), int(self.winfo_height() / 2),
            image=self.img_lose,
            anchor=CENTER,
            tags="info")

        self.game_canvas.tag_raise(lose)

        lose = self.game_canvas.create_text(
            int(self.section_col1_w / 2), self.section_field_y - 8,
            text=reason,
            anchor=S,
            fill="#00ff00",
            font=('Helvetica', 16),
            tags="info")
        self.game_canvas.tag_raise(lose)

        self.running = False
        return 'get_version'

    def game_win(self, *args):
        self.game_STATE = "WIN_GAME"
        self.config(cursor="heart")
        _print("[" + str(self.TP.num) + "]",
               "> You win.")

        s = int(self.winfo_height() * 0.66)

        self.img_win = ImageTk.PhotoImage(self.img_win_raw.resize((s, s), Image.ANTIALIAS))
        self.game_canvas.create_image(
            int(self.section_col1_w / 2), int(self.winfo_height() / 2),
            image=self.img_win,
            anchor=CENTER,
            tags="info")

        self.running = False
        return 'get_version'

    def get_player_path(self, *args):
        def get_pre(pre_a, t):
            p_range = [pre_a]
            reached = False
            while not reached:
                pre_step = []
                for pre_n in p_range:
                    for pre_a in self.city[pre_n].get('con'):
                        pre_append = True
                        for pre_check in pre_step:
                            if pre_check == pre_a:
                                pre_append = False
                        if pre_append:
                            pre_step.append(pre_a)
                            if pre_a == t:
                                return pre_n
                for pre_s in pre_step:
                    pre_append = True
                    for pre_check in p_range:
                        if pre_check == pre_s:
                            pre_append = False
                    if pre_append:
                        p_range.append(pre_s)

        if self.logistician > 3:
            aktpos = self.TP.pos
        else:
            aktpos = self.all_player_pos[self.logistician]

        # get distance to specific city
        if len(args) > 0:
            target = args[0]
            path = [target]
            while get_pre(aktpos, target) != aktpos:
                path.append(get_pre(aktpos, target))
                target = get_pre(aktpos, target)
            return path
        # update player_range
        else:
            self.TP.set_range([aktpos])
            for r in range(0, self.TP.turns['LEFT']):
                step = []
                for n in self.TP.range:
                    for a in self.city[n].get('con'):
                        append = True
                        for check in step:
                            if check == a:
                                append = False
                        if append:
                            step.append(a)
                for s in step:
                    append = True
                    for check in self.TP.range:
                        if check == s:
                            append = False
                    if append:
                        self.TP.range_append(s)
            self.TP.range_remove(aktpos)

    def receive_card(self, *args):
        _print("[" + str(self.TP.num) + "]",
               args)
        # get args from response
        if len(args) > 0:

            update = False

            # receive player cards
            if 'new_cards' in args[0] and self.game_STATE == "SUPPLY":
                self.TP.set_dc(args[0]['new_cards'])
                self.txt_status[0] = "Nachschubphase"
                self.TP.set_turns("turn", 0)
                update = True

            # receive infection cards for epidemie (inf x 3)
            if 'new_epi' in args[0] and self.game_STATE == "EPIDEMIE":
                old = self.TP.drawcards
                self.TP.set_dc([args[0]['new_epi'][0]])
                for o in old:
                    self.TP.dc_append(o)
                _print("[" + str(self.TP.num) + "]",
                       ">>> EPIDEMIE >>>", str(self.TP.drawcards))
                update = True

            # receive regular infection cards
            if 'new_inf' in args[0] and self.game_STATE == "INFECT":
                if len(args[0]['new_inf']) > 0:
                    self.TP.set_dc(args[0]['new_inf'])
                    self.txt_status[0] = "Infektionsphase"
                    update = True
                else:  # action silent night
                    self.txt_status[0] = "Überspringe Infektionsphase. (Ereigniskarte 'Eine ruhige Nacht')"

            if "action48" in args[0]:
                # no card update
                self.TP.set_turns('sender', "response")
                self.TP.set_turns('args', args[0]['action48'])

            if "action50" in args[0]:
                # no card update
                self.TP.set_turns('sender', "response")
                self.TP.set_turns('args', args[0]['action50'])

            if 'role3' in args[0]:
                # no card update
                self.TP.set_turns('sender', "response")
                self.TP.set_turns('card', args[0]['role3'])

            if update:
                self.gameupdatelist['cards'].append(7)

        return 'getVersion'

    def city2card(self, args):
        numcards = []
        for num, card in enumerate(self.TP.cards):
            if card in args:
                numcards.append(num)
        return numcards

    def check_exchange(self, *param):

        send = False
        receive = False
        sender = []         # list of players that can send cards
        receiver = []       # list of players that can receive cards from player
        send_cards = []     # list of cards the currend player can send

        # check if more then one player in city
        if self.all_player_pos.count(self.TP.pos) > 1:

            if self.TP.pos in self.TP.cards:  # player has citycard
                send = True
                send_cards.append(self.TP.pos)

            if self.TP.role == 4:        # player is role 4
                for c in self.TP.cards:  # and has at least one citycard
                    if c < 48:
                        send = True
                        if c not in send_cards:
                            send_cards.append(c)
            if send:
                for num, p in enumerate(self.all_player_pos):  # append other players to receiver
                    if p == self.TP.pos and\
                            num not in receiver and\
                            self.all_player_name[num] != "" and\
                            num != self.TP.num:
                        receiver.append(num)

            for num, p in enumerate(self.all_player_pos):  # other player has cards
                if p == self.TP.pos and num != self.TP.num:

                    if self.all_player_pos[num] in self.all_player_cards[num]:   # other player has citycard
                        receive = True
                        if num not in sender:
                            sender.append(num)
                    if self.all_player_role[num] == 4:          # other player is role 4
                        for c in self.all_player_cards[num]:    # and has at least one citycard
                            if c < 48:
                                receive = True
                                if num not in sender:
                                    sender.append(num)

        response = {
            "send": send,
            "receive": receive,
            "sender": sender,
            "receiver": receiver,
            "send_cards": send_cards
            }
        if len(param) > 0:
            return response.get(str(param[0]), (send + receive))
        else:
            return send + receive

    def exchange_card(self):

        if self.TP.exchange['status'] == "request":
            if self.TP.exchange['c'] == 99 and self.TP.num == self.TP.exchange['s']:
                # card not set, this player is sender
                # choose card to give or decline (Turn 500)
                self.TP.cs_reset()
                self.draw_card_highlight()
                print(">>> X >>> exchange_card REQUEST s", self.TP.exchange)
                self.txt_status[1] = str(self.all_player_name[self.TP.exchange['r']]) + \
                                     " möchte eine Karte von dir haben."
                self.draw_card_highlight(self.city2card(self.check_exchange("send_cards")), "G")
                # create decline button
                self.game_canvas.create_image(
                    self.section_col1_w - math.floor(self.section_toolbar_h) * 13 - 4 + math.floor(self.section_toolbar_h) / 2,
                    self.section_toolbar_y - 16,
                    image=self.img_c_over[14],
                    activeimage=self.img_c_over[15],
                    anchor=S,
                    tags=("BTN_500", "popup", "toclick")
                )
                self.game_canvas.tag_bind("BTN_500", "<ButtonRelease-1>",
                                          lambda event, tag="BTN_500": self.game_click(event, tag))

                self.TP.set_turns('turn', 500)  # create turn 500 (any state) to set card. then execute

            elif self.TP.exchange['c'] != 99 and self.TP.num == self.TP.exchange['r']:
                print(">>> X >>> exchange_card REQUEST r", self.TP.exchange)
                # everything set, player is receiver
                # accept or decline card
                self.TP.cs_reset()
                self.draw_card_highlight()
                self.txt_status[1] = "Du erhältst eine Karte von " + str(self.all_player_name[self.TP.exchange['s']])
                self.TP.dc_append(self.TP.exchange['c'])
                self.gameupdatelist['cards'].append(7)

                self.TP.set_turns('turn', 501)  # create turn 501 (anystate) to update card. then execute

        elif self.TP.exchange['status'] == "done":
            self.txt_status[1] = ""  # TODO custom text?

        self.gameupdatelist['exchange'] = 0
    # endregion

    # region ###### DRAW ###############################################################################################
    # TODO
    def draw_visual(self):

        def draw_path(f, t):
            tag = "waytag" + str(f) + str(t)
            self.game_canvas.create_line(
                int(self.city[f]['X'] * float(int(self.section_col1_w)) / 100),
                int(self.city[f]['Y'] * float(int(self.section_col1_w / 2.125) / 100) + self.section_field_y),
                int(self.city[t]['X'] * float(int(self.section_col1_w)) / 100),
                int(self.city[t]['Y'] * float(int(self.section_col1_w / 2.125) / 100) + self.section_field_y),
                fill="#ffaa00", width=2, tags=tag)
            time.sleep(5)
            if self.running:
                self.game_canvas.delete(tag)

        self.gameupdatelist['visual'] = 0

        if 'move' in self.visual:
            print("VISUAL",
                self.all_player_name[self.visual['move'][0]],
                  "bewegt sich von",
                  self.city[self.visual['move'][1]]['name'],
                  "nach",
                self.city[self.visual['move'][2]]['name']
            )
            # self.logtext(self.city[self.visual['move'][1]]['name'])

            threading.Thread(target=draw_path, args=(self.visual['move'][1], self.visual['move'][2],)).start()

# city
    def draw_cities(self, aw):
        def inf_value(e):
            return e['value']

        c = self.city[aw]
        self.game_canvas.delete("c" + str(c.get('ID')))
        card_h = self.section_card_h - 8
        s_inf = 320 * self.section_col1_w / (3380 * 2)  # variable for marker size (half the size)
        s_cen = s_inf * 120 / 320

        # temporary infection item for current city
        infection = [{'i': 0, 'value': 0}, {'i': 1, 'value': 0}, {'i': 2, 'value': 0}, {'i': 3, 'value': 0}]
        for i in range(0, 4):
            infection[i]['value'] = c['i'][i]

        # sort infection (highest value first -> highest infection will be drawn on most inner ring
        infection.sort(key=inf_value, reverse=True)

        # get anchor-position of city (center)
        x = int(c.get('X') * float(int(self.section_col1_w)) / 100)
        y = int(c.get('Y') * float(int(self.section_col1_w / 2.125) / 100) + self.section_field_y)

        for i in range(0, 4):  # loop infection rings
            if infection[i].get('value') > 0:
                inf = infection[i].get('i')
                v = infection[i].get('value')
                for n in range(0, v):
                    self.game_canvas.create_image(x, y,
                                                  image=self.img_inf[n][inf][i],
                                                  anchor=CENTER,
                                                  tags=("c" + str(c.get('ID')), "inf"))
            else:
                break

        if c.get('c') == 1:
            x = int(c.get('X') * float(int(self.section_col1_w)) / 100) - int(s_cen / 120 * 82)
            y = int(c.get('Y') * float(int(self.section_col1_w / 2.125) / 100) + self.section_field_y) + int(
                s_cen / 120 * 50)
            self.game_canvas.create_image(x, y,
                                          image=self.img_center,
                                          anchor=CENTER,
                                          tags=("c" + str(c.get('ID')), "center"))
        # draw 'zaeh' indicator
        if aw in self.special_val['a50']:
            self.game_canvas.create_image(x, y,
                                          image=self.img_zaeh,
                                          anchor=CENTER,
                                          tags=("c" + str(c.get('ID')), "zaeh"))

        self.gameupdatelist['city'] = []

    def draw_city_highlight(self, *args):
        self.game_canvas.delete("city_highlight")
        if len(args) > 0:
            for aw in args[0]:
                if aw < 48:
                    c = self.city[aw]

                    # get anchor-position of city (center)
                    x = int(c.get('X') * float(int(self.section_col1_w)) / 100)
                    y = int(c.get('Y') * float(int(self.section_col1_w / 2.125) / 100) + self.section_field_y)
                    r = (self.section_col1_w * 0.0125)

                    citytag = "CITY" + str(aw)

                    if len(args) > 1:  # action
                        param = dict(outline=args[1], fill="", width=2, activewidth=2, activefill=args[1])
                    else:
                        param = dict(outline="#00ff00", fill="", activefill="#ff0000")

                    param['tags'] = "city_highlight", citytag, "toclick"
                    self.game_canvas.create_oval(x - r, y - r, x + r, y + r, param)

                    self.game_canvas.tag_bind(citytag, "<ButtonRelease-1>",
                                              lambda event, t=citytag: self.game_click(event, t))

# selection
    def draw_disease_selection(self, *cnum):
        self.game_canvas.delete("disease_selection")
        if len(cnum) > 0:  # draw selection
            c = self.city[cnum[0]]
            size = int(self.section_col1_w / 35)

            # cities at the right
            toleft = False
            if cnum[0] in [37, 39, 42, 43, 46, 47]:
                toleft = True

            # get anchor-position of city (center)
            x = int(c.get('X') * float(int(self.section_col1_w)) / 100) + size / 2
            y = int(c.get('Y') * float(int(self.section_col1_w / 2.125) / 100) + self.section_field_y) + 15

            if toleft:
                x -= size

            pos = 0
            for num, i in enumerate(c.get('i')):
                if i > 0:
                    param = dict(activeoutline="#ffffff", activewidth=2)

                    param['fill'] = get_inf_color(num)
                    param['activefill'] = get_inf_color(num)
                    param['outline'] = get_inf_color(num)

                    diseasetag = "DIS_" + str(num)
                    param['tags'] = "disease_selection", diseasetag, "toclick", "popup"

                    if not toleft:
                        self.game_canvas.create_oval(x + (size + 5) * pos, y - size / 2, x + (size + 5) * pos + size,
                                                     y + size / 2,
                                                     param)
                    else:
                        # param['anchor'] = SW
                        self.game_canvas.create_oval(x - (size + 5) * pos - size, y - size / 2, x - (size + 5) * pos,
                                                     y + size / 2,
                                                     param)
                    pos += 1

                    self.game_canvas.tag_bind(diseasetag, "<ButtonRelease-1>",
                                              lambda event, t=diseasetag: self.game_click(event, t))

    def draw_player_selection(self, *args):
        self.game_canvas.delete("player_selection")
        if len(args) > 0:  # draw selection   self.draw_player_selection(selected_player, "LOG2")
            if len(args[0]) > 0:
                players = args[0]
                c = self.city[self.all_player_pos[players[0]]]
                size = int(self.section_col1_w / 35)

                # default, draw at city
                # get anchor-position of city (center)
                x = int(c.get('X') * float(int(self.section_col1_w)) / 100) + size / 2
                y = int(c.get('Y') * float(int(self.section_col1_w / 2.125) / 100) + self.section_field_y) + 15
                # if second argument available, try to override position
                if len(args) > 1:
                    if args[1] == "action49":
                        if 49 in self.TP.cards:
                            pass
                            # x = 8 + (8 + int((self.section_col1_w - 72) / 8)) * self.TP.cards.index(49)
                            # y = self.section_card_h + 8 + 3
                        else:  # role3extra
                            x = self.special_val['pos'][0] + self.section_card_h / 20 * 7 + 8
                            y = self.special_val['pos'][1] - size

                for pos, p in enumerate(players):
                    role = self.all_player_role[p]
                    param = dict(activeoutline="#ffffff", activewidth=2)
                    param['fill'] = get_role_color(role)
                    param['activefill'] = get_role_color(role)
                    param['outline'] = get_role_color(role)

                    playertag = "PLAY" + str(p)
                    param['tags'] = "player_selection", playertag, "toclick", "popup"

                    self.game_canvas.create_oval(x + (size + 5) * pos, y, x + (size + 5) * pos + size, y + size, param)

                    self.game_canvas.tag_bind(playertag, "<ButtonRelease-1>",
                                              lambda event, t=playertag: self.game_click(event, t))

# cards
    def carddim(self, requesttype, *num):

        area_w = math.floor(self.section_col1_w / 8)
        border_w = area_w - 4
        card_w = border_w - 6

        card_h = card_w / 7 * 10
        border_h = card_h + 6

        if requesttype == "size":
            return int(card_w), int(card_h)

        if requesttype == "pos":
            return 6 + (card_w + 10) * num[0], 6

        if requesttype == "bg":
            return am_rect(2 + area_w * num[0], 2, border_w, border_h)

        if requesttype == "high_size":
            return int(border_w), int(border_h)

        if requesttype == "high_pos":
            return 6 + (card_w + 10) * num[0] - 3, 3

        if requesttype == "overlay":
            card_w = int((self.section_col1_w - 72) / 8)
            card_h = int((self.section_col1_w - 72) / 8 / 7 * 10)
            return int(8 + (8 + card_w) * (num[0] + 1) + card_w / 2), \
                   int(self.section_card_h + (card_h / 3) + card_h / 2)

        if requesttype == "sel48":
            card_w = int((self.section_col1_w - 72) / 8)
            card_h = int((self.section_col1_w - 72) / 8 / 7 * 10)
            return int(8 + (8 + card_w) * (num[0] + 1) + card_w / 2), \
                   int( + card_h / 2 + 2)

    def draw_cards(self, card_in, card_pos):
        # Draw cards at cardregion
        if card_pos == 0 and card_in != 99:
            self.game_canvas.delete("card" + str(card_in))

            # region  ###### draw player cards ######
            if card_in < len(self.TP.cards):
                card = self.TP.cards[card_in]
                self.img_c1[card] = ImageTk.PhotoImage(
                    self.img_c1_raw[card].resize(self.carddim("size"), Image.ANTIALIAS))
                self.game_canvas.create_image(
                    self.carddim("pos", card_in), image=self.img_c1[card], anchor=NW, tags="card" + str(card_in))
            # endregion

            # region ###### draw card pile ######
            if len(self.TP.drawcards) > 0:  # drawcard
                if self.TP.drawcards[0] not in self.TP.cards:  # only resize if not in playercards
                    self.img_c1[self.TP.drawcards[0]] = ImageTk.PhotoImage(
                        self.img_c1_raw[self.TP.drawcards[0]]
                            .resize((self.carddim("size")), Image.ANTIALIAS))
                self.game_canvas.create_image(
                    self.carddim("pos", 7), image=self.img_c1[self.TP.drawcards[0]], anchor=NW, tags="cards")

                # draw overlay (infect)
                if self.game_STATE == "INFECT" or self.game_STATE == "EPIDEMIE":
                    self.img_c2 = ImageTk.PhotoImage(
                        self.img_c2_raw.resize((self.carddim("size")), Image.ANTIALIAS))
                    self.game_canvas.create_image(
                        self.carddim("pos", 7), image=self.img_c2, anchor=NW, tags="cards")
            # draw back
            else:
                if self.game_STATE == "INFECT":
                    self.img_c2_back = ImageTk.PhotoImage(
                        self.img_c2_back_raw.resize((self.carddim("size")), Image.ANTIALIAS))
                    self.game_canvas.create_image(
                        self.carddim("pos", 7), image=self.img_c2_back, anchor=NW, tags="cards")
                else:
                    self.img_c1[54] = ImageTk.PhotoImage(
                        self.img_c1_raw[54].resize((self.carddim("size")), Image.ANTIALIAS))
                    self.game_canvas.create_image(
                        self.carddim("pos", 7), image=self.img_c1[54], anchor=NW, tags="cards")
            # endregion

            # optional draw role 3 card
            if card_in == 9 and self.TP.role == 3 and self.special_val['r3'] != 0:
                self.game_canvas.delete("icon_4")
                self.img_c1[self.special_val['r3']] = \
                    ImageTk.PhotoImage(self.img_c1_raw[self.special_val['r3']]
                                       .resize((int(self.carddim("size")[0] / 2),
                                                int(self.carddim("size")[1] / 2)),
                                                Image.ANTIALIAS))

                self.game_canvas.create_image(self.special_val['pos'],
                                              image=self.img_c1[self.special_val['r3']],
                                              anchor=SW,
                                              tags='role3extra')

            self.draw_card_highlight()
            self.gameupdatelist['cards'] = []

        # draw cards on canvas, action 48 or 8
        elif card_pos == 8 and card_in != 99:
            # remove highlights
            self.draw_card_highlight(None)
            self.dismiss_tooltip()
            self.game_canvas.delete("popup_high")

            card_w = int((self.section_col1_w - 72) / 8)
            card_h = int((self.section_col1_w - 72) / 8 / 7 * 10)

            # display title
            if len(card_in) > 0:
                t = self.game_canvas.create_text(8 + (8 + card_w), self.section_card_h + (card_h / 3) - 2,
                                                 text="Spielerfähigkeit",
                                                 fill="#ffffff",
                                                 anchor=SW,
                                                 font=('Helvetica', 12, 'bold'),
                                                 tags=("popup", "popup_high", "toclick"))
                self.game_canvas.create_text(
                    16 + (8 + card_w) + self.game_canvas.bbox(t)[2] - self.game_canvas.bbox(t)[0],
                    self.section_card_h + (card_h / 3) - 2,
                    text="Wähle Karte aus",
                    fill="#ffffff",
                    anchor=SW,
                    font=('Helvetica', 10),
                    tags=("popup", "popup_high", "toclick"))
            # display cards
            for pos, c in enumerate(card_in):
                # card
                scale_card = True
                if c in self.TP.cards:
                    scale_card = False
                if len(self.TP.drawcards) > 0:
                    if self.TP.drawcards[0] == c:
                        scale_card = False

                if scale_card:
                    self.img_c1[c] = ImageTk.PhotoImage(self.img_c1_raw[c]
                                                        .resize((int(card_w), int(card_h)), Image.ANTIALIAS))
                cardtag = "CARD" + str(pos)
                param = dict(image=self.img_c1[c],
                             anchor=CENTER,
                             tags=("popup", "popup_high", cardtag, "toclick"))

                self.game_canvas.create_image(self.carddim("overlay", pos),
                                              param)

                self.draw_card_highlight([self.TP.turns['card'].index(c)],
                                                   "G",
                                                    "selectactioncard")
        elif card_pos == 48 and card_in != 99:
            # remove highlights
            self.draw_card_highlight(None)
            self.dismiss_tooltip()
            self.game_canvas.delete("popup_high")

            card_w = int((self.section_col1_w - 72) / 8)
            card_h = int((self.section_col1_w - 72) / 8 / 7 * 10)
            pos_y = 24  # self.section_card_h + (card_h / 3) - 2

            if len(card_in) > 0:
                # create BG  TODO define in init
                self.img_sel48bg = ImageTk.PhotoImage(Image.new(
                    'RGBA',
                    (self.carddim("sel48", len(card_in))[0] + 8 - self.carddim("sel48", 0)[0],
                     card_h + 24 + pos_y),
                    color=(0, 0, 0, 192)))
                self.game_canvas.create_image((8 + card_w), 0,
                                              image=self.img_sel48bg,
                                              anchor='nw',
                                              tags=("popup", "toclick"))
                # accept button
                self.game_canvas.create_image(
                    8 + card_w,
                    card_h + pos_y + 24,
                    image=self.img_btn[0][0],
                    activeimage=self.img_btn[1][0],
                    anchor=NW,
                    tags=("BTN_48", "popup", "toclick")
                )
                self.game_canvas.tag_bind("BTN_48", "<ButtonRelease-1>",
                                          lambda event, tag="BTN_48": self.game_click(event, tag))
                # close button
                self.game_canvas.create_image(
                    8 + card_w + 41,
                    card_h + pos_y + 24,
                    image=self.img_btn[0][1],
                    activeimage=self.img_btn[1][1],
                    anchor=NW,
                    tags=("BTN_481", "popup", "toclick")
                )
                self.game_canvas.tag_bind("BTN_481", "<ButtonRelease-1>",
                                          lambda event, tag="BTN_481": self.game_click(event, tag))
                # display title
                t = self.game_canvas.create_text(8 + (8 + card_w), pos_y,
                                                 text="Ereignis: Prognose",
                                                 fill="#ffffff",
                                                 anchor=SW,
                                                 font=('Helvetica', 12, 'bold'),
                                                 tags=("popup", "popup_high", "toclick"))
                self.game_canvas.create_text(
                    16 + (8 + card_w) + self.game_canvas.bbox(t)[2] - self.game_canvas.bbox(t)[0],
                    pos_y,
                    text="Sortiere Karten neu",
                    fill="#ffffff",
                    anchor=SW,
                    font=('Helvetica', 10),
                    tags=("popup", "popup_high", "toclick"))
                # display cards
                for pos, c in enumerate(card_in):
                    # card
                    scale_card = True
                    if c in self.TP.cards:
                        scale_card = False
                    if len(self.TP.drawcards) > 0:
                        if self.TP.drawcards[0] == c:
                            scale_card = False

                    if scale_card:
                        self.img_c1[c] = ImageTk.PhotoImage(self.img_c1_raw[c]
                                                            .resize((int(card_w), int(card_h)), Image.ANTIALIAS))
                    cardtag = "CARD" + str(pos)

                    self.game_canvas.create_image(
                        self.carddim("sel48", pos)[0],
                        self.carddim("sel48", pos)[1] + pos_y,
                        image=self.img_c1[c],
                        anchor=CENTER,
                        tags=("popup", "popup_high", cardtag, "toclick", "moveC"))

                    self.game_canvas.tag_bind(cardtag, "<ButtonPress-1>",
                                              lambda event, tag=cardtag: self.dnd_down(event, tag))
                    self.game_canvas.tag_bind(cardtag, "<ButtonRelease-1>", self.dnd_up)
                    # text (cardnumber)
                    self.game_canvas.create_text(8 + (8 + card_w) * (pos + 1),
                                                     card_h + 6 + pos_y,
                                                     text=str(pos + 1) + ". Karte",
                                                     fill="#ffffff",
                                                     anchor=NW,
                                                     font=('Helvetica', 10),
                                                     tags=("popup", "popup_high", "toclick"))

    def draw_card_highlight(self, *args):

        self.game_canvas.delete("card_highlight")

        if len(args) == 0:  # region DEFAULT: Draw highlight, depending on state
            self.game_canvas.delete("card_highlight_sel")
            if len(self.TP.drawcards) > 0:
                if self.TP.drawcards[0] == self.card_epidemie \
                        or self.game_STATE == "INFECT" \
                        or self.game_STATE == "EPIDEMIE":
                    # Epidemie
                    self.game_canvas.create_image(
                        self.carddim("high_pos", 7),
                        image=self.img_c_over[0],
                        activeimage=self.img_c_over[5],
                        anchor=NW,
                        tags=("card_highlight", "toclick")
                    )

                else:
                    self.game_canvas.create_image(
                        self.carddim("high_pos", 7),
                        image=self.img_c_over[2],
                        activeimage=self.img_c_over[4],
                        anchor=NW,
                        tags=("card_highlight", "toclick", "conf7")
                    )
                    if self.game_STATE == "SUPPLY" or self.game_STATE == "PASSIV":
                        for bg in range(0, 7):
                            if bg < len(self.TP.cards):
                                self.game_canvas.create_image(
                                    self.carddim("high_pos", bg),
                                    image=self.img_c_over[2],
                                    activeimage=self.img_c_over[3],
                                    anchor=NW,
                                    tags=("card_highlight", "toclick", "cardhigh"+str(bg), "conf"+str(bg))
                                )
                            else:
                                self.game_canvas.create_image(
                                    self.carddim("high_pos", bg),
                                    image=self.img_c_over[0],
                                    activeimage=self.img_c_over[1],
                                    anchor=NW,
                                    tags=("card_highlight", "toclick", "cardhigh"+str(bg))
                                )

                self.game_canvas.tag_bind("card_highlight", "<Enter>", self.draw_tooltip)
                self.game_canvas.tag_bind("card_highlight", "<Leave>", self.dismiss_tooltip)
                self.game_canvas.tag_bind("card_highlight", "<ButtonRelease-1>", self.game_click)
        # endregion
        else:
            if args[0] is None:  # region delete all special highlights when first arg is 'None'
                self.game_canvas.delete("card_highlight_sel")
                self.game_canvas.delete("actioncard")
            # endregion
            else:  # region specific changes
                scolor = {
                    "R": [2, 7],  # TODO should never happen
                    "G": [0, 6],
                    "H": [6, 7]
                }
                param = dict(image=self.img_c_over[scolor.get(args[1], [0, 0])[0]],
                             activeimage=self.img_c_over[scolor.get(args[1], [0, 0])[1]],
                             anchor=NW)

                if len(args) > 2:
                    param['tags'] = (args[2], "toclick")
                    if args[2] == "actioncard":  # actioncard (small at side)
                        for bg in args[0]:
                            param['tags'] = param['tags'] + ("cardhigh" + str(bg),)
                            if bg != 9:
                                self.game_canvas.create_image(self.carddim("high_pos", bg), param)
                            else:
                                param['tags'] = (args[2], "toclick")
                                param['image'] = self.img_c_over[9]
                                param['activeimage'] = self.img_c_over[8]
                                param['anchor'] = SW
                                self.game_canvas.create_image(self.special_val['pos'], param)
                            self.game_canvas.tag_bind("actioncard", "<ButtonRelease-1>",
                                                      lambda event, t="CARD" + str(bg): self.game_click(event, t))
                        self.game_canvas.tag_bind("actioncard", "<Enter>", self.draw_tooltip_action)
                        self.game_canvas.tag_bind("actioncard", "<Leave>", self.dismiss_tooltip)

                    elif args[2] == "selectactioncard":
                        for bg in args[0]:
                            param['tags'] = ("CARD"+str(bg), args[2], "toclick", "popup", "cardhigh" + str(bg))
                            param['anchor'] = CENTER
                            self.game_canvas.create_image(self.carddim("overlay", bg), param)
                            self.game_canvas.tag_bind("CARD"+str(bg), "<ButtonRelease-1>",
                                                      lambda event, t="CARD"+str(bg): self.game_click(event, t))

                            self.game_canvas.tag_bind("CARD"+str(bg), "<Enter>", self.draw_tooltip_action)
                            self.game_canvas.tag_bind("CARD"+str(bg), "<Leave>", self.dismiss_tooltip)
                    elif args[2] == "card_highlight_sel":
                        param['tags'] = "card_highlight_sel"
                        for bg in args[0]:
                            self.game_canvas.itemconfig("cardhigh" + str(bg),
                                                        image=self.img_c_over[scolor.get(args[1])[0]],
                                                        activeimage=self.img_c_over[scolor.get(args[1])[1]]
                                                        )
                        self.game_canvas.tag_bind("card_highlight_sel", "<ButtonRelease-1>", self.game_click)
                    elif args[2] == "select_space":
                        for bg in range(0, 7):
                            if bg < len(self.TP.cards):
                                self.game_canvas.create_image(
                                    self.carddim("high_pos", bg),
                                    image=self.img_c_over[2],
                                    activeimage=self.img_c_over[3],
                                    anchor=NW,
                                    tags=("card_highlight", "toclick", "cardhigh"+str(bg), "conf"+str(bg))
                                )
                            else:
                                self.game_canvas.create_image(
                                    self.carddim("high_pos", bg),
                                    image=self.img_c_over[0],
                                    activeimage=self.img_c_over[1],
                                    anchor=NW,
                                    tags=("card_highlight", "toclick", "cardhigh"+str(bg))
                                )
                        self.game_canvas.tag_bind("card_highlight", "<ButtonRelease-1>", self.game_click)
                else:
                    for bg in args[0]:
                        param['tags'] = ("card_highlight_sel", "cardhigh" + str(bg))
                        self.game_canvas.create_image(self.carddim("high_pos", bg), param)
                    self.game_canvas.tag_bind("card_highlight_sel", "<ButtonRelease-1>", self.game_click)

# drag and drop
    def dnd_down(self, event, *args):
        self.game_canvas.tag_raise(args[0])

        self.action_48['down'] = args[0][4:]
        if "moveC" in self.game_canvas.gettags(CURRENT):
            event.widget.bind("<Motion>", self.dnd_motion)

    def dnd_motion(self, event):
        self.config(cursor="exchange")
        cnv = event.widget
        x, y = cnv.canvasx(event.x), cnv.canvasy(event.y)
        # check 3. and 4th value  -> , event.widget.winfo_width() + x, event.widget.winfo_height() + y
        event.widget.coords(tk.CURRENT, x, y)

    def dnd_up(self, event):
        self.config(cursor="")
        event.widget.unbind("<Motion>")

        up = (math.floor(float(event.x) / (self.section_col1_w / 8)))-1

        if 0 <= up < len(self.action_48['cards']) and up != self.action_48['down']:

            switch = self.action_48['cards'][up]
            self.action_48['cards'][up] = self.action_48['cards'][int(self.action_48['down'])]
            self.action_48['cards'][int(self.action_48['down'])] = switch

        self.draw_cards(self.action_48['cards'], 48)

# elements
    def draw_toolbar(self, *args):
        def check_ico(btnnum, icon, state):

            if self.game_canvas.itemcget(self.toolbar[btnnum], 'image') != self.img_icon[state][icon]:
                if state:
                    self.game_canvas.itemconfigure(self.toolbar[btnnum], image=self.img_icon[1][icon],
                                               activeimage=self.img_icon[2][icon])
                else:
                    self.game_canvas.itemconfigure(self.toolbar[btnnum], image=self.img_icon[0][icon],
                                               activeimage="")
                if icon == 0:  # not visible
                    self.game_canvas.itemconfigure(self.toolbar[btnnum], tags="toolbar")
            if not state:  # and self.game_canvas.itemcget(self.toolbar[btnnum], 'activeimage') is not None:
                self.game_canvas.itemconfigure(self.toolbar[btnnum], activeimage="")

        # region --- info ---
        # icon state:
        #   0 = inactive/ not available
        #   1 = active/available
        #   2 = highlighted
        # icons:
        #    0: empty
        #    1: empty
        #    2: build center
        #    3: cure desease
        #    4: share knowledge
        #    5: invent
        #    6: actioncard
        #    7: player krisenmanager
        #    8: move
        #    9: fly direct
        #   10: fly charter
        #   11: fly special (center)
        #   12: move other player OR betriebsexperte
        #   13: move player to player
        #   14: empty
        #   15: reload
        #   16: ent turn
        # endregion

        if len(args) == 0:  # draw_new
            self.game_canvas.delete("toolbar")
            # self.game_canvas.create_rectangle(
            #     am_rect(0, self.section_toolbar_y, self.section_col1_w, int(self.section_toolbar_h)),
            #     fill="#282828", outline='#282828', tags="toolbar")
            self.toolbar = []
            for btn in range(0, 17):
                singletag = "btn_" + str(btn)
                self.toolbar.append(self.game_canvas.create_image(
                    # align right and floor value to prevent different spacings
                    self.section_col1_w - math.floor(self.section_toolbar_h) * (17 - btn),
                    self.section_toolbar_y,
                    image=self.img_icon[0][btn],
                    anchor=NW, tags=("toolbar", "btn", singletag)))
                if btn in {0, 1, 14}:
                    self.game_canvas.delete(singletag)

        # customize cards and highlights

        # TODO
        # TODO pos = self.all_player_pos[self.logistician] if self.logistician < 3 else self.TP.pos
        # TODO move_player = self.logistician if self.logistician < 3 else self.TP.num
        if self.current_player == self.TP.num and self.TP.turns['LEFT'] > 0:
            # player is active and has turns left

            # build center only if player has card or is role 7 and no center in city already
            if (self.TP.pos in self.TP.cards or \
                self.TP.role == 7) and not \
                    self.city[self.TP.pos].get("c"):
                check_ico(2, 2, 1)
            else:
                check_ico(2, 2, 0)

            # cure disease only if city is infected
            show_icon = False
            for c in range(0, 4):
                if self.city[self.TP.pos]['i'][c] > 0:
                    show_icon = True
                    break
            check_ico(3, 3, show_icon)

            # share knowledge only if there are more than one player in same city
            check_ico(4, 4, self.check_exchange())

            # heale desease
            # only if city has center
            if self.city[self.TP.pos].get("c"):
                check = [0, 0, 0, 0]
                for c in self.TP.cards:
                    if c <= 47:
                        check[self.city[c].get("d")] += 1
                for idf, f in enumerate(check):
                    if f > 4 or (self.TP.role == 1 and f > 3):
                        if self.healing[idf] == 0:
                            check_ico(5, 5, 1)
                            break
            else:
                check_ico(5, 5, 0)

            # role 3 only
            if self.TP.role == 3 and self.special_val["r3"] == 0:
                check_ico(7, 7, 1)
            else:
                check_ico(7, 7, 0)

            # move (with turns left always possible)
            check_ico(8, 8, 1)

            # Direktflug:             turn   :  Zielstadt = Karte auf der Hand -> Karte abwerfen
            # fly direct with destination card
            show_icon = False
            if self.TP.role == 5 and self.logistician < 4:  # logistiker
                for c in self.TP.cards:
                    if c != self.all_player_pos[self.logistician] and c < 48:
                        show_icon = True
                        break
            else:
                for c in self.TP.cards:
                    if c != self.TP.pos and c < 48:
                        show_icon = True
                        break
            check_ico(9, 9, show_icon)

            # Charterflug:            turn   :  Startstadt = Karte auf der Hand -> Karte abwerfen
            # fly charter
            show_icon = False
            if self.TP.role == 5 and self.logistician < 4:  # logistiker
                if self.all_player_pos[self.logistician] in self.TP.cards:
                    show_icon = True
            else:
                if self.TP.pos in self.TP.cards:
                    show_icon = True
            check_ico(10, 10, show_icon)

            # fly special only if city has center
            show_icon = False
            if self.TP.role == 5 and self.logistician < 4:  # logistiker
                if self.city[self.all_player_pos[self.logistician]].get("c"):
                    for c in self.city:
                        if c.get("c") and c.get("ID") != self.all_player_pos[self.logistician]:
                            show_icon = True
                            break
            else:
                if self.city[self.TP.pos].get("c"):
                    for c in self.city:
                        if c.get("c") and c.get("ID") != self.TP.pos:
                            show_icon = True
                            break
            check_ico(11, 11, show_icon)

            # two functions on one button (12)
            if self.TP.role == 5:  # logistiker
                check_ico(12, 12, 1)
                show_icon = False
                for p in self.all_player_pos:
                    if self.all_player_pos.count(p) < 4 - self.all_player_role.count(0):
                        show_icon = True
                if show_icon:
                    check_ico(13, 13, 1)
                else:
                    check_ico(13, 13, 0)
            elif self.TP.role == 7:  # betriebsexperte
                if self.city[self.TP.pos].get("c"):
                    for c in self.TP.cards:
                        if c < 48 and c != self.TP.pos:
                            check_ico(12, 18, 1)
                            break
                else:
                    check_ico(12, 18, 0)
            else:
                check_ico(12, 0, 1)
                check_ico(13, 0, 1)

            check_ico(16, 16, 1)

        else:
            check_ico(2, 2, 0)
            check_ico(3, 3, 0)
            check_ico(4, 4, 0)
            check_ico(5, 5, 0)
            check_ico(7, 7, 0)
            check_ico(8, 8, 0)
            check_ico(9, 9, 0)
            check_ico(10, 10, 0)
            check_ico(11, 11, 0)
            if self.TP.role == 5:
                check_ico(12, 12, 0)
                check_ico(13, 13, 0)
            elif self.TP.role == 7:
                check_ico(12, 18, 0)
                check_ico(13, 0, 0)
            else:
                check_ico(12, 0, 0)
                check_ico(13, 0, 0)

            if self.current_player == self.TP.num \
                    and self.game_STATE == "SUPPLY" and len(self.TP.drawcards) == 0:
                check_ico(16, 17, 1)
            else:
                check_ico(16, 16, 0)

        # actioncard
        show_icon = False
        for c in self.TP.cards:
            if c >= 48:
                show_icon = True

        if show_icon or (self.special_val["r3"] != 0 and self.TP.role == 3):
            check_ico(6, 6, 1)
        else:
            check_ico(6, 6, 0)

        check_ico(15, 15, 1)

        self.game_canvas.tag_bind("btn", "<ButtonRelease-1>", self.game_click)
        self.game_canvas.tag_bind("btn", "<Enter>", self.draw_tooltip)
        self.game_canvas.tag_bind("btn", "<Leave>", self.dismiss_tooltip)

    def draw_sidebar(self):
        # region sidebar: 10:25

        # CARDS     -  0: titel
        # CARDS     -  1: current player
        # CARDS     -  2: next player
        # CARDS     -  3: next player
        # CARDS     -  4: next player
        # CARDS     -  5: next player
        # STATUS    -  6: heal header
        # FIELD     -  7: heal
        # FIELD     -  8: heal
        # FIELD     -  9: infection header
        # FIELD     - 10: infection
        # FIELD     - 11: outbreak header
        # FIELD     - 12: outbreak
        # FIELD     - 13: remaining infection header
        # FIELD     - 14: remaining infection
        # FIELD     - 15: remaining infection
        # FIELD     - 16: supply header
        # FIELD     - 17: supply
        # FIELD     - 18: log header
        # FIELD     - 19: log
        # FIELD     - 20: log
        # FIELD     - 21: log
        # FIELD     - 22: log
        # TOOLBAR   - 23: log
        # TOOLBAR   - 24: log
        # endregion

        def sidebar_pos(x, y, w, h):
            offset_x = self.section_side_x
            offset_y = 0
            tilesize = self.section_side_row_h

            return [int(offset_x + x * tilesize),
                    int(offset_y + y * tilesize),
                    int(offset_x + x * tilesize + w * tilesize),
                    int(offset_y + y * tilesize + h * tilesize)]

        # fontsize
        fs = int((self.section_side_row_h - 6.6475) / 1.4951)
        if fs > 8:
            fs = math.floor((fs - 8) / 2 + 8)

        # only update relevant parts:
        # region --- Stats ---
        # region --- Cards / other Players ---
        if "CP" in self.gameupdatelist['sidebar'] or \
                "PC" in self.gameupdatelist['sidebar']:

            pos_y = 2

            # CP = playercards      -> update cards
            # PC = current player   -> update player order
            self.otherplayer = []
            for p in range(0, (4 - self.all_player_role.count(0))):
                player = (self.current_player + p) % (4 - self.all_player_role.count(0))
                self.otherplayer.append([player])
                self.otherplayer[p].append(self.all_player_cards[player].copy())
                self.otherplayer[p][1].sort()

            # draw
            self.game_canvas.delete("op")

            minicard_h = self.section_side_row_h - 4
            minicard_w = minicard_h / 10 * 7

            for pr, p in enumerate(self.otherplayer):
                # rise first row
                if pr == 0:
                    r = int(self.section_side_row_h * (pos_y - 0.5))
                else:
                    r = int(self.section_side_row_h * (pos_y + pr))

                param = dict(fill="#cc7474", outline='#222', tags=("otherplayerrole", "toclick", "op"))
                param['fill'] = get_role_color(self.all_player_role[p[0]])

                # player role color
                self.game_canvas.create_rectangle(
                    am_rect(self.section_col1_w + self.section_side_row_h * 0.5 + 3,
                            r,
                            minicard_w,
                            minicard_h),
                    param)
                # player cards
                for c in range(0, 7):
                    if len(p[1]) > c:
                        switcher = {
                            0: "#3069bf",  # 006bfd
                            1: "#bfb830",  # fff300
                            2: "#2a701c",  # 189300
                            3: "#bd2f2f",  # f10000
                            4: "#9d3d9e"
                        }
                        self.game_canvas.create_rectangle(
                            am_rect(self.section_col1_w + self.section_side_row_h * 1.5 + (minicard_w + 4) * c,
                                    r,
                                    minicard_w,
                                    minicard_h),
                            fill=switcher.get(int((p[1][c] - p[1][c] % 12) / 12)),
                            outline='#222',
                            tags=("otherplayercard", "toclick", "op"))

                    else:
                        self.game_canvas.create_rectangle(
                            am_rect(self.section_col1_w + self.section_side_row_h * 1.5 + (minicard_w + 4) * c,
                                    r, minicard_w, minicard_h),
                            fill="#333",
                            outline='#282828',
                            tags="op")

                self.game_canvas.create_text(
                    self.section_col1_w + self.section_side_row_h * 1.5 + (minicard_w + 4) * 7,
                    r + self.section_side_row_h / 2,
                    text=self.all_player_name[p[0]],
                    anchor=W,
                    fill="#ffffff",
                    font=('Helvetica', fs),
                    tags="op")

            self.game_canvas.tag_bind("otherplayerrole", "<Enter>", self.draw_tooltip_player)
            self.game_canvas.tag_bind("otherplayerrole", "<Leave>", self.dismiss_tooltip)
            self.game_canvas.tag_bind("otherplayercard", "<Enter>", self.draw_tooltip_othercards)
            self.game_canvas.tag_bind("otherplayercard", "<Leave>", self.dismiss_tooltip)
        # endregion

        if "SH" in self.gameupdatelist['sidebar']:
            pos_y = 8
            # State Healing
            for h in range(0, 4):
                if len(self.game_canvas.find_withtag("sbSH"+str(h))) == 0:  # draw new if nonexistant
                    self.game_canvas.create_image(sidebar_pos(1 + h * 2, pos_y, 1, 1)[0],
                                                  sidebar_pos(1 + h, pos_y, 1, 1)[1],
                                                  image=self.img_icon[0][19 + h],
                                                  anchor=NW, tags="sbSH"+str(h))
                self.game_canvas.itemconfig("sbSH"+str(h),
                                           image=self.img_icon[self.healing[h]][19 + h])

        if "SL" in self.gameupdatelist['sidebar']:
            pos_y = 11
            # State Infection lvl
            if len(self.game_canvas.find_withtag("sbSL")) == 0:  # draw new if nonexistant
                self.game_canvas.create_rectangle(1, 1, 1, 1, fill="#ff9c00", outline='', tags="sbSL")
            self.game_canvas.coords(self.game_canvas.find_withtag("sbSL"),
                                    sidebar_pos(0.5, pos_y, self.inflvl + 1, 1))

        if "SO" in self.gameupdatelist['sidebar']:
            pos_y = 13
            # State Outbreak lvl
            if len(self.game_canvas.find_withtag("sbSO")) == 0:  # draw new if nonexistant
                self.game_canvas.create_rectangle(1, 1, 1, 1, fill="#ff9c00", outline='', tags="sbSO")
            self.game_canvas.coords(self.game_canvas.find_withtag("sbSO"),
                                    sidebar_pos(0.5, pos_y, self.outbreak + 1, 1))

        if "SI" in self.gameupdatelist['sidebar']:
            pos_y = 15
            # State Infection (4 values)
            for i in range(0, 4):
                if self.infection[i] < 24:
                    if len(self.game_canvas.find_withtag("sbSI"+str(i))) == 0:  # draw new if nonexistant
                        self.game_canvas.create_rectangle(1, 1, 1, 1, fill=get_inf_color(i), outline='', tags="sbSI"+str(i))
                    self.game_canvas.coords(self.game_canvas.find_withtag("sbSI"+str(i)),
                                        sidebar_pos(0.5, pos_y + (i * 9/25), (25 - self.infection[i]) * 9 / 25, 9 / 25))

        if "SS" in self.gameupdatelist['sidebar']:
            pos_y = 18
            # State Supply remaining (max: 59)
            # rectangle
            if len(self.game_canvas.find_withtag("sbSS1")) == 0:  # draw new if nonexistant
                self.game_canvas.create_rectangle(1, 1, 1, 1, fill="#4eff00", outline='', tags="sbSS1")
            self.game_canvas.coords(self.game_canvas.find_withtag("sbSS1"),
                                    sidebar_pos(0.5, pos_y, 1, 1))
            if self.supplies < 1:
                self.game_canvas.itemconfig("sbSS1", fill="#ff4e00")
            else:
                self.game_canvas.itemconfig("sbSS1", fill="#4eff00")
            # bar
            if len(self.game_canvas.find_withtag("sbSS2")) == 0:  # draw new if nonexistant
                self.game_canvas.create_rectangle(1, 1, 1, 1, fill="#4eff00", outline='', tags="sbSS2")
            self.game_canvas.coords(self.game_canvas.find_withtag("sbSS2"),
                                    sidebar_pos(1.5, pos_y + 0.333, 8 / 59 * self.supplies, 0.33))
            # text
            if len(self.game_canvas.find_withtag("sbSS3")) == 0:  # draw new if nonexistant
                self.game_canvas.create_text(
                    sidebar_pos(1, pos_y + 0.5, 1, 1)[0],
                    sidebar_pos(1, pos_y + 0.5, 1, 1)[1],
                    text=self.supplies,
                    anchor=CENTER,
                    fill="#000000",
                    font=('Helvetica', fs),
                    tags="sbSS3")
            self.game_canvas.itemconfig("sbSS3", text=self.supplies, font=('Helvetica', fs))
        # endregion

        # log
        pos_y = 20
        if len(self.game_canvas.find_withtag("logtext")) == 0:  # draw new if nonexistant
            self.game_canvas.create_text(
                sidebar_pos(0.5, pos_y, 1, 1)[0],
                sidebar_pos(0.5, pos_y, 1, 1)[1],
                text="",
                anchor=NW,
                fill="#FFF",
                font=('Helvetica', fs-2),
                tags="logtext")

        # overlay
        self.game_canvas.tag_raise("side_overlay")
        self.game_canvas.tag_raise("op")

        self.gameupdatelist['sidebar'] = []

    def draw_player(self):
        self.game_canvas.delete("player")
        # player 80x175
        s_inf = 320 * self.section_col1_w / (3380 * 2)  # variable for marker size (half the size)
        s_cen = s_inf * 120 / 320
        h_ply = s_cen * 175 / 120
        w_ply = s_cen * 80 / 120
        for c in self.city:
            draw_pos = 0  # reset player
            for p in range(0, 4):
                if self.all_player_pos[p] == c.get('ID') and self.all_player_role[p] != 0:
                    draw_pos += 1
                    self.img_p[self.all_player_role[p] - 1] = ImageTk.PhotoImage(
                        self.img_p_raw[self.all_player_role[p] - 1]
                            .resize((int(w_ply), int(h_ply)), Image.ANTIALIAS))
                    x = int(c.get('X') * float(int(self.section_col1_w)) / 100) \
                        - int(s_cen / 120 * 39) \
                        + int(s_cen / 120 * 52) * draw_pos
                    y = int(c.get('Y') * float(int(self.section_col1_w / 2.125) / 100) + self.section_field_y) \
                        - int(s_cen / 120 * 41)
                    self.game_canvas.create_image(
                        x, y, image=self.img_p[self.all_player_role[p] - 1], anchor=CENTER, tags="player")

        self.gameupdatelist['playerpos'] = 0

# tooltip
    def logtext(self, *textin):

        if len(textin) > 0:

            for line in range(0, 7):
                self.logtextcontent[line] = self.logtextcontent[line+1]
            self.logtextcontent[7] = str(textin[0])

            displaytext = ""
            for line in range(0, 8):
                displaytext = displaytext + "\n" + self.logtextcontent[7 - line]

            fs = int((self.section_side_row_h - 6.6475) / 1.4951)
            if fs > 8:
                fs = math.floor((fs - 8) / 2 + 8)

            self.game_canvas.itemconfig("logtext", text=displaytext, font=('Helvetica', fs - 2))

    def draw_tooltip(self, event):
        if event.y >= self.section_toolbar_y - 3:  # BUTTONS
            posx = self.game_canvas.coords(tk.CURRENT)[0] + event.widget.winfo_width() / 34
            num = math.floor(float(posx) / self.section_col1_w * 17)

            # 2 functions on one button
            if num == 12 and self.TP.role != 5:
                if self.TP.role != 7:
                    num = 0
                else:
                    num = 17

            if num == 7 and self.TP.role != 3:
                num = 0  # no tooltip if not player 3

            if (num == 12 or num == 13) and self.TP.role != 5:
                num = 0  # no tooltip if not player 5

            switcher = {
                0: "",
                2: "Forschungscenter errichten",
                3: "Krankheit behandeln",
                4: "Wissen teilen",
                5: "Heilmittel entdecken",
                6: "Ereigniskarte spielen",
                7: "Krisenmanager",
                8: "Autofahrt/Schifffahrt",
                9: "Direktflug",
                10: "Charterflug",
                11: "Sonderflug",
                12: "Bewege anderen Spieler",
                13: "Bewege Spieler zu Spieler",
                15: "reload",
                16: "Zug beenden",
                17: "Betriebsexperte",
            }

            self.game_canvas.itemconfigure(self.i_quicktip, anchor=S, fill="white", text=(switcher.get(num)))
            self.game_canvas.coords(self.i_quicktip, posx, self.section_toolbar_y - 6)
        else:  # CARDS
            posx = self.game_canvas.coords(tk.CURRENT)[0] + event.widget.winfo_width() / 16
            num = math.floor(float(posx) / self.section_col1_w * 8)

            if len(self.TP.cards) <= num:
                text = "Karte aufnehmen"
            else:
                text = "Karte ersetzen"
            if num == 7:
                if self.TP.drawcards[0] != self.card_epidemie:
                    if self.game_STATE == "SUPPLY":
                        text = "Karte verwerfen"
                    if self.game_STATE == "INFECT":
                        text = "Infizieren"
                    if self.game_STATE == "EPIDEMIE":
                        text = "Epidemieausbruch"
                    if self.game_STATE == "PASSIV":
                        text = "Karte nicht annehmen"
                else:
                    text = "Epidemie auslösen"

            self.game_canvas.itemconfigure(self.i_quicktip,
                                           fill="white",
                                           text=text,
                                           anchor=S)
            self.game_canvas.coords(self.i_quicktip, posx, self.section_card_h + 24)

        self.draw_tooltip_bg(self.i_quicktip)

    def draw_tooltip_action(self, event):
        if self.game_canvas.coords(tk.CURRENT)[1] <= self.section_card_h:
            posx = self.game_canvas.coords(tk.CURRENT)[0] + 8
            posy = self.section_card_h + 10
            num = math.floor(float(posx) / self.section_col1_w * 8)
            card = self.TP.cards[num]
            self.game_canvas.itemconfigure(self.i_quicktip, anchor=NW)
        else:  # adjust pos if info for role3extra
            if self.special_val['r3'] == 0:  # selection on field
                getcard = (next((s for s in self.game_canvas.gettags(tk.CURRENT) if "CARD" in s), None))
                if getcard is not None:
                    card = self.TP.turns['card'][int(getcard[4:])]

                posx = self.game_canvas.bbox(tk.CURRENT)[2] + 8
                posy = self.game_canvas.bbox(tk.CURRENT)[3]
                self.game_canvas.itemconfigure(self.i_quicktip, anchor=SW)
            else:  #
                posx = self.game_canvas.coords(tk.CURRENT)[0] * 2 + 8
                posy = self.game_canvas.coords(tk.CURRENT)[1]
                card = self.special_val['r3']
                self.game_canvas.itemconfigure(self.i_quicktip, anchor=SW)

        switcher = {
            48: "Prognose\n\n"
                "Sieh dir die obersten\n"
                "6 Karten des Nachzieh-\n"
                "stapels an und ordne\n"
                "sie neu.",
            49: "Freiflug\n\n"
                "Bewege eine beliebige\n"
                "Spielfigur in eine\n"
                "beliebige Stadt.",
            50: "Zähe Bevölkerung\n\n"
                "Wähle eine Karte aus dem\n"
                "Infektions-Ablagestapel\n"
                "und entferne sie aus dem\n"
                "Spiel.",
            51: "Staatliche Subvention\n\n"
                "Errichte ein Forschungs-\n"
                "zentrum ohne Karte in\n"
                "einer beliebigen Stadt.",
            52: "Eine ruhige Nacht\n\n"
                "Die nächste Infektions-\n"
                "phase wird komplett\n"
                "übersprungen."
        }

        self.game_canvas.itemconfigure(self.i_quicktip,
                                       fill="white",
                                       text=switcher.get(card))
        self.game_canvas.coords(self.i_quicktip, posx, posy)
        self.game_canvas.tag_raise(self.i_quicktip)

        self.draw_tooltip_bg(self.i_quicktip)

    def draw_tooltip_player(self, event):

        switcher = {
            1: "Wissenschaftlerin\n"
               "Bei der Aktion 'Heilmittel entdecken'\n"
               "benötigst du nur 4 statt 5 Karten.",
            2: "Quarantänespezialistin\n"
               "An deinem Standort und an jeder an-\n"
               "grenzenden Stadt werden niemals Seuchen\n"
               "plaziert.",
            3: "Krisenmanager\n"
               "Suche als Aktion eine beliebige\n"
               "Ereigniskarte aus dem Ablagestapel\n"
               "heraus und verwende sie erneut.",
            4: "Forscherin\n"
               "Du kannst bei der Aktion 'Wissen teilen'\n"
               "jede Stadtkarte tauschen.",
            5: "Logistiker\n"
               "- Bewege die Spielfigur eines Mit-\n"
               "  spielers als wäre es deine eigene.\n"
               "- Bewege als Aktion eine beliebige\n"
               "  Spielfigur in eine Stadt, in der sich\n"
               "  bereits eine andere Figur befindet.",
            6: "Sanitäter\n"
               "Bei der Aktion 'Seuche behandeln'\n"
               "entfernst du alle Würfel einer Farbe.\n"
               "Geheilte Seuchen entfernst du auto-\n"
               "matisch von deinem Standort",
            7: "Betriebsexperte\n"
               "- Um ein Forschungszentrum zu errichten\n"
               "  brauchst du keine Karte.\n"
               "- Bewege als Aktion (einmal pro Zug)\n"
               "  deine Figur von einem Forchungszentrum\n"
               "  in eine beliebige Stadt.\n"
               "  Wirf dafür eine beliebige Stadtkarte ab."
        }

        param = dict(fill="white")

        if event.x < self.section_col1_w:
            # configure info on field for Player
            x = int(6 + ((self.section_col1_w - 6) / 8) / 2 + 4) + 2
            y = int(self.section_field_y + self.section_field_h - 8) - 2
            param['anchor'] = SW
            param['text'] = "Du bist: " + switcher.get(self.TP.role)

        else:
            # configure info for other players
            x = self.section_col1_w + self.section_side_row_h/2 - 3
            y = (event.y - event.y % self.section_side_row_h) + self.section_side_row_h / 2
            card_y = math.floor((round(self.game_canvas.coords(tk.CURRENT)[1] / self.section_side_row_h * 2)) / 2 - 1.5)
            param['anchor'] = E
            param['text'] = switcher.get(self.all_player_role[self.otherplayer[card_y][0]])

        self.game_canvas.itemconfigure(self.i_quicktip, param)
        self.game_canvas.coords(self.i_quicktip, x, y)
        self.game_canvas.tag_raise(self.i_quicktip)
        self.draw_tooltip_bg(self.i_quicktip)

    def draw_tooltip_othercards(self, event):

        card_x = round(
            (self.game_canvas.coords(tk.CURRENT)[0] - (self.section_col1_w + self.section_side_row_h * 1.5)) /
            (((self.section_side_row_h - 4) / 10 * 7) + 4))
        card_y = math.floor((round(self.game_canvas.coords(tk.CURRENT)[1] / self.section_side_row_h * 2)) / 2 - 1.5)

        param = dict(fill="white")

        x = self.game_canvas.coords(tk.CURRENT)[0] + (self.section_side_row_h - 4) / 20 * 7
        y = self.game_canvas.coords(tk.CURRENT)[1] - 5
        param['anchor'] = S
        cardnum = self.otherplayer[card_y][1][card_x]
        if cardnum < 48:
            param['text'] = self.city[cardnum].get('name')
        else:
            switcher = {
                48: "Prognose",
                49: "Freiflug",
                50: "Zähe Bevölkerung",
                51: "Staatliche Subvention",
                52: "Eine ruhige Nacht"
            }
            param['text'] = switcher.get(cardnum)

        self.game_canvas.itemconfigure(self.i_quicktip, param)
        self.game_canvas.coords(self.i_quicktip, x, y)
        self.game_canvas.tag_raise(self.i_quicktip)
        self.draw_tooltip_bg(self.i_quicktip)

    def draw_tooltip_bg(self, obj):
        size = self.game_canvas.bbox(obj)
        self.img_quicktip_bg = ImageTk.PhotoImage(Image.new('RGBA',
                                                            (size[2] - size[0] + 4, size[3] - size[1] + 4),
                                                            color=(0, 0, 0, 192)))
        r = self.game_canvas.create_image(size[0] - 2, size[1] - 2,
                                          image=self.img_quicktip_bg,
                                          anchor='nw',
                                          tags=("abg", "info"))
        self.game_canvas.tag_lower(r, obj)

    def dismiss_tooltip(self, *event):
        self.game_canvas.delete("abg")
        self.game_canvas.itemconfigure(self.i_quicktip, fill="")
    # endregion


_log()
_print("START")

app = Client()
app.mainloop()

app.running = False
print("wait for exit...")
_log("EXIT")
