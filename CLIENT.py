#!/usr/bin/env python3
import socket
import selectors
import traceback
import tkinter as tk
from tkinter import *
import urllib.request
import ctypes
import math
import time
import threading
from PIL import Image, ImageTk
import inspect

from Pandemie import libclient

# TODO Aktionskarten
#   48: Prognose
#   49: Freiflug
#   50: zähle Bevölkerung
#   51: staatliche Subvention
#   52: eine ruhige Nacht

# TODO Player spezialfunktionen:
#   3: action 1a: zusätzliche aktionskarte aus ablegestapel
#      action 1b: spiele diese karte

# TODO pos status and actiontext is wrong when window higher than wide
# TODO action 14 + 15 for player role 5: other player must agree movement


########################################################################################################################
update_intervall = 3000
port = 9999
res_path = "D:/_PROJEKTE/2020/Python/Pandemie/"
php_path = "http://moja.de/public/python/getip.php"
# -------------------------------------------------------------------------------------------------------------------- #
trans = '@D:/_PROJEKTE/2020/Python/Pandemie/mat/transparent.xbm'
full = '@D:/_PROJEKTE/2020/Python/Pandemie/mat/full.xbm'
AM_DEBUG_OUTPUT = True
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
# FLOW #################################################################################################################
#
# Client()
#   init var
#   init resources
#   > self.window_00_load()
#      > start Thread(target=self.load_res_async)
#         try to get ip for server from php-script
#         load res, while updating window
#      < done when self.load[2] == 3
#   > self.window_01_connect()
#      user can modify IP
#      self.btn_con                                     self.btn_recon
#      > self.window_02a_game_prep                      > self.window_02b_recon
#                                                          self.btn_recon
#                                                          player enters his number [0..3]
#                                                          if entrie is valid:
#   start self.task()                                   start self.task()
# ----------------------------------------------------------------------------------------------------------------------
# Mainloop
#   request = create_request(self.action, self.value)
#   repeats request every update_intervall
#   > gameclient(self, m_response, m_version)
#       gameclient checks for response - response only available after request != getVersion
# ----------------------------------------------------------------------------------------------------------------------
#  02a_game_prep                                        02b_recon
#    create_request('getVersion', "INIT")                 create_request('recon', self.this_player_num)
#    loop and update
#      when serverversion != localversion
#       get_init_update ->
#           update player_name                            update player_name
#           update player_role                            update player_role
#    BTN btn_player_enter                                 set self.this_player_isrdy = 1
#      action: set_player
#       set > self.this_player_num
#    loop and update
#    BTN btn_player_rdy
#      action = 'player_rdy'
#      self.this_player_isrdy = 1
#  >>> awaits server                                      >>> server should be ready
#  self.start_game
#     self.game_status = "GAME"
#     self.action = 'get_update'

# callback -> click-auswertung
#
#   1 choose action (btn)
#       btn_action_selector -> switch to function
#       > btn_##_turn_...(self)
#           set this_player_turns['turn'] = #
#           calculate required data for turn if nessecary
#           draw highlights
#           set self.txt_turn_info
#       > callback
#           awaits click
#           complet this_player_turns
#       > btn_31_turn_execute
#           send data to server
#           update local data
#           clear field
#
# endregion


# region custum functions and classes
def _print(*args):
    if AM_DEBUG_OUTPUT:
        line = ""
        for txt in args:
            line = line + " " + str(txt)
        if len(args) > 0:
            line += " > "
        print(line + inspect.stack()[1].__getattribute__("function"))


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
        _print()
        self.sel = selectors.DefaultSelector()

        # region game variable #########################################################################################
        # player
        self.all_player_name = ['', '', '', '']
        self.all_player_role = [0, 0, 0, 0]
        self.all_player_pos = [2, 2, 2, 2]  # start in Atlanta
        self.all_player_cards = [[], [], [], []]

        self.this_player_num = 0
        self.this_player_cards = []
        self.this_player_card_selection = []
        self.this_player_drawcards = []
        self.this_player_range = []

        self.this_player_turns = {'sender': "", 'turn': 0, 'turns_left': 0}
        self.this_player_exchange = {'status': "", 'sender': 0, 'card': 0, 'receiver': 0}
        self.exchange = []

        self.logistician = 5
        self.actioncard = False

        # request
        self.host = ''
        self.action = 'get_init_update'
        self.value = {'v': 0}

        self.update_client = False
        self.running = False
        self.block_request = False

        # connection / loading
        self.ctrl_res_load = [0, 90, 0]  # [act load, total load, ready]
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
        self.gameupdatelist = {'city': [], 'cards': [], 'marker1': 0, 'marker2': 0, 'playerpos': 0}

        # dimensions
        self.section_game_w = 1
        self.section_card = 0
        self.section_field = 0
        self.section_status = 0
        self.section_action = 0

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
        self.img_status_raw = Image  # statusbar
        self.img_status = ImageTk
        self.img_action_raw = Image  # actionbar
        self.img_action = ImageTk

        self.img_icon_raw = []  # additional icons
        self.img_icon = []

        self.img_char_raw = []  # character cards
        self.img_char = []
        self.img_c1_raw = []  # player cards [00..53]
        self.img_c1 = []
        self.img_c2_back_raw = Image  # infectioncard, back
        self.img_c2_back = ImageTk
        self.img_c2_raw = Image  # infectioncard, back
        self.img_c2 = ImageTk
        self.img_inf_raw = []  # infection marker: inf_0_1.png
        self.img_inf = []
        self.img_center_raw = Image  # center
        self.img_center = ImageTk
        self.img_p_raw = []  # player_piece
        self.img_p = []
        self.img_win_raw = Image
        self.img_win = ImageTk
        self.img_lose_raw = Image
        self.img_lose = ImageTk

        # region window 00 connection load
        self.LOADframe = Frame(self)
        self.load_canvas = ResizingCanvas(self.LOADframe, width=512, height=140, highlightthickness=0)
        self.loading_bar = self.load_canvas.create_rectangle(am_rect(8, 72, 0, 5), fill="#09f", outline="")
        self.load_canvas.create_text(8, 70, text='connect to server...', anchor='sw', tags="loadingtext")
        # endregion

        # region window 01 connection connect
        self.title("Pandemie | Verbindung")

        if AM_DEBUG_OUTPUT:
            self.geometry("512x140+758+1")
        else:
            self.geometry("512x140")

        self.CONframe = Frame(self)

        self.header = Label(self.CONframe, text="Verbindung:", font="Helvetica 24 bold")
        self.addr_frame = Frame(self.CONframe)
        self.btn_frame = Frame(self.CONframe)
        self.btn_con = Button(self.btn_frame, width="30", text='START', justify="center",
                              command=self.window_02a_game_prep)
        self.btn_recon = Button(self.btn_frame, text='reconnect',
                                command=self.window_02b_recon)
        self.entry1 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.l1 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.entry2 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.l2 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.entry3 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.l3 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.entry4 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        # endregion

        # region window 02A/B preparation
        self.PREPframe = Frame(self)
        self.lbl1 = Label(self.PREPframe, text="Name", font="Helvetica 14 bold")
        self.entry_n = tk.Entry(self.PREPframe, width="16", justify="left", font="Helvetica 14 bold")
        self.btn_participate = Button(self.PREPframe, text='Teilnehmen', command=self.btn_init_signin)
        self.btn_start = Button(self.PREPframe, text='Spiel starten', command=self.btn_init_player_rdy, state=DISABLED)
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
        self.btn_startrecon = Button(self.recon_frame, text='START', justify="center", command=self.btn_init_recon)
        self.recon_stat = Label(self, text="")
        # endregion

        # region window game UI
        self.game_frame = Frame(self)
        self.lbl_empty = Label(self, text="loading...")
        self.old_window_w = 0
        self.old_window_h = 0
        self.game_canvas = ResizingCanvas(self.game_frame, width=1, height=1, bg="#333", highlightthickness=0)

        self.i_quicktip = self.game_canvas.create_text(0, 0)
        self.i_actiontip = self.game_canvas.create_text(0, 0)
        self.i_action = Label(self.game_canvas)
        self.i_status = Label(self.game_canvas)
        self.txt_action = ""
        self.txt_status = ""
        # endregion

        self.window_00_load()

        # endregion

    # region ###### UI #################################################################################################
    def window_00_load(self):

        if self.ctrl_res_load[0] == 0:  # INIT
            _print()
            self.LOADframe.pack()
            self.load_canvas.pack()

            self.ctrl_res_load[0] += 1  # end init
            thread1 = threading.Thread(target=self.window_00_load_async)
            thread1.start()

        if self.ctrl_res_load[2] == 1:  # switch text after connectiondata is loaded
            self.load_canvas.delete("loadingtext")
            self.load_canvas.create_text(8, 70, text='loading resources...', anchor='sw', tags="loadingtext")
            self.ctrl_res_load[2] = 2

        if self.ctrl_res_load[2] == 2:  # load rescources and display bar
            x0, y0, x1, y1 = self.load_canvas.coords(self.loading_bar)
            self.load_canvas.coords(
                self.loading_bar, x0, y0, (512 - 21) * self.ctrl_res_load[0] / self.ctrl_res_load[1] + 5, y1)

        if self.ctrl_res_load[2] == 3:  # leave loop and start connection window
            # self.set_after(self.window_01_connect, 500)
            self.after(500, self.window_01_connect)
        else:  # loop self
            # self.set_after(self.window_00_load, 1)
            self.after(1, self.window_00_load)

    def window_00_load_async(self):

        _print("  start")
        self.config(cursor="wait")
        # connection
        # try to get ip for server from php-script
        self.ip_am = urllib.request.urlopen(php_path).read().decode('utf8').strip()
        self.ip_parts = self.ip_am.split(".")

        self.ctrl_res_load[2] = 1

        #                             [0] increment
        self.ctrl_res_load[1] = 90  # [1] total number of elements to load
        #                             [2] boolean to 1 when ready

        self.img_map_raw = Image.open(res_path + "mat/world.png")
        self.img_map = ImageTk.PhotoImage(self.img_map_raw)
        self.ctrl_res_load[0] += 1

        self.img_overlay_game_raw = Image.open(res_path + "mat/namen.png")
        self.img_overlay_game = ImageTk.PhotoImage(self.img_overlay_game_raw)
        self.ctrl_res_load[0] += 1

        self.img_action_raw = Image.open(res_path + "mat/actionbar.png")
        self.img_action = ImageTk.PhotoImage(self.img_action_raw)
        self.ctrl_res_load[0] += 1

        self.img_status_raw = Image.open(res_path + "mat/statusbar.png")
        self.img_status = ImageTk.PhotoImage(self.img_status_raw)
        self.ctrl_res_load[0] += 1

        self.img_center_raw = Image.open(res_path + "mat/center.png")
        self.img_center = ImageTk.PhotoImage(self.img_center_raw)
        self.ctrl_res_load[0] += 1

        for c in range(0, 55):
            # print(str(c))
            self.img_c1_raw.append(Image.open(res_path + "cards/c1_" + "{:02d}".format(c) + ".png"))
            self.img_c1.append(ImageTk.PhotoImage(self.img_c1_raw[c]))
            self.ctrl_res_load[0] += 1

        self.img_c2_back_raw = Image.open(res_path + "cards/c2_0.png")
        self.img_c2_back = ImageTk.PhotoImage(self.img_c2_back_raw)
        self.ctrl_res_load[0] += 1

        self.img_c2_raw = Image.open(res_path + "cards/c2_overlay.png")
        self.img_c2 = ImageTk.PhotoImage(self.img_c2_raw)
        self.ctrl_res_load[0] += 1

        self.img_win_raw = Image.open(res_path + "mat/win.png")
        self.img_win = ImageTk.PhotoImage(self.img_win_raw)
        self.ctrl_res_load[0] += 1

        self.img_lose_raw = Image.open(res_path + "mat/lose.png")
        self.img_lose = ImageTk.PhotoImage(self.img_lose_raw)
        self.ctrl_res_load[0] += 1

        for c in range(0, 8):
            self.img_char_raw.append(Image.open(res_path + "cards/char_" + str(c) + ".png"))
            self.img_char.append(ImageTk.PhotoImage(self.img_char_raw[c].resize((350, 500), Image.ANTIALIAS)))
            self.ctrl_res_load[0] += 1

        self.role_image = Label(self.PREPframe, image=self.img_char[0])

        self.ctrl_res_load[0] += 1

        self.img_inf_raw = [[Image.open(res_path + "mat/inf_" + str(x) + "_" + str(y + 1) + ".png") for x in range(4)]
                            for y in range(4)]

        self.ctrl_res_load[0] += 2

        self.img_inf = [[[ImageTk.PhotoImage(self.img_inf_raw[x][y]) for x in range(4)] for y in range(4)] for z in
                        range(3)]

        self.ctrl_res_load[0] += 2

        for p in range(0, 7):
            self.img_p_raw.append(Image.open(res_path + "mat/player_" + str(p + 1) + ".png"))
            self.img_p.append(ImageTk.PhotoImage(self.img_p_raw[p]))
            self.ctrl_res_load[0] += 1

        for ico in range(0, 6):
            self.img_icon_raw.append(Image.open(res_path + "mat/icon_" + str(ico) + ".png"))
            self.img_icon.append(ImageTk.PhotoImage(self.img_icon_raw[ico]))
            self.ctrl_res_load[0] += 1

        self.config(cursor="")
        # loading done
        _print("  done ")
        self.ctrl_res_load[2] = 3

    def window_01_connect(self):
        _print()
        self.LOADframe.destroy()

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
        if AM_DEBUG_OUTPUT:
            self.btn_con.bind('<Return>', self.window_02b_recon)
        else:
            self.btn_con.bind('<Return>', self.window_02a_game_prep)

    def window_02a_game_prep(self, *event):
        _print()
        # global client_host
        self.host = self.entry1.get() + '.' + self.entry2.get() + '.' + self.entry3.get() + '.' + self.entry4.get()
        print(self.host)

        self.CONframe.destroy()

        self.title("Spielvorbereitung")

        if AM_DEBUG_OUTPUT:
            self.geometry("700x600+758+1")
        else:
            self.geometry("700x600")

        self.PREPframe.grid()
        self.lbl1.grid(row=0, column=1, padx=5, pady=18, sticky=E)
        self.entry_n.grid(row=0, column=2, padx=5, pady=18, sticky=W + E)
        self.btn_participate.grid(row=0, column=3, padx=5, pady=18, sticky=W)
        self.btn_start.grid(row=0, column=4, padx=5, pady=18, sticky=W)
        self.lbl2.grid(row=1, column=1, padx=5, pady=0, sticky=W + S, columnspan=2)
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
        _print()
        # global client_host
        self.host = self.entry1.get() + '.' + self.entry2.get() + '.' + self.entry3.get() + '.' + self.entry4.get()
        _print("reconnect", self.host)

        self.CONframe.destroy()

        self.title("Reconnect")

        if AM_DEBUG_OUTPUT:
            self.entry_re.insert(0, "0")

        self.recon_frame.pack(side=TOP, pady=(40, 0))
        self.recon_label.pack(side="left")
        self.entry_re.pack(side="left")
        self.btn_startrecon.pack(side="right", padx=(10, 0), pady=5)
        self.recon_stat.pack(side="bottom")

        self.btn_startrecon.focus_set()
        self.btn_startrecon.bind('<Return>', self.btn_init_recon)

    def btn_init_signin(self):
        _print("BTN")
        playername = self.entry_n.get()
        if playername != "":
            self.entry_n.configure(state=DISABLED)
            self.btn_participate.configure(state=DISABLED)
            self.action = "player_signin"
            self.value = {'v': self.localversion, 'player_name': playername.strip()}

    def btn_init_player_rdy(self):
        _print("BTN")
        self.btn_start.configure(bg="SeaGreen1", text="Warte auf andere Spieler", state=DISABLED)
        self.game_STATE = "WAIT"
        self.action = 'player_rdy'
        self.value = {'v': self.localversion, 'player_num': self.this_player_num}

    def btn_init_recon(self, event=None):
        _print("BTN")
        try:
            num = int(self.entry_re.get())
            if 0 <= num < 4:
                print("reconnect player:", str(num))
                self.this_player_num = num

                self.action = 'recon'
                # self.value = {'v': self.localversion, 'num': num}
                self.recon_frame.destroy()
                self.start_main()

            else:
                self.recon_stat.config(text="invalid player, enter 'Player No.' from 0 to 3")
        except ValueError:
            self.recon_stat.config(text="invalid entry, enter numeric value from 0 to 3")
            print("Exeption")

    def start_main(self):
        self.send_request()
        self.running = True
        threading.Thread(target=self.delay_request).start()
    # endregion

    # region ###### connection #########################################################################################
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
                        print(
                            "main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}",
                            e
                        )
                        self.report_error("Player " + str(self.this_player_num) + " Request Error:")
                        message.close()
                # Check for a socket being monitored to continue.
                if not self.sel.get_map():
                    break
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
    # endregion

    # region ###### game ###############################################################################################
    def game_engine(self, m_response):

        m_version = m_response.get("v") if "v" in m_response else None
        _print(str(m_response), self.game_STATE, m_response.get("state"))

        # update game button
        if self.this_player_turns['turn'] == 33 and self.this_player_turns['sender'] == "BTN":
            self.draw_city_highlight()
            self.localversion = 0

        # region MANAGE requests #######################################################################################
        if m_response.get("R"):
            switcher = {
                # RESPONSE after request ------------------------------------------------
                "init_update":  self.game_init_update,
                "player_set":   self.game_init_player_set,
                "recon":        self.game_init_recon,
                "update":       self.game_update,
                "new_cards":    self.receive_card,
                "count":        self.action_count_population,
                # GLOBAL RESPONSE - STATE-CHANGE ----------------------------------------
                "GAME":         self.game_init_execute_game,
                "LOSE_GAME":    self.game_lose,
                "WIN_GAME":     self.game_win,

            }
            func = switcher.get(m_response.get("R"), lambda r: None)  # returns new action for request
            newaction = func(m_response)  # execute

            func = switcher.get(m_response.get("state"), lambda: None)
            stateaction = func()

            _print(self.game_STATE, newaction, stateaction)

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
                        print("FAILURE: unknown game status")
                        self._update('getVersion')
                        self.txt_status = "FAILURE: unknown game status"
                else:
                    # unblock
                    self.block_request = False
                    self.config(cursor="")
                    self.value = {'v': self.localversion}
                    self.action = 'getVersion'
            else:
                print("FAILURE: Game Engine - No response")
        # endregion
        # region MANAGE state ##########################################################################################

        # region ###### actions for any state
        # ---  7 - start actioncard ---------------------------------------------------------------------------------- #
        if self.this_player_turns['turn'] == 7:
            if self.this_player_turns['sender'] == "BTN":
                self.this_player_card_selection = []
                for c in self.this_player_cards:
                    if c > 47:
                        self.txt_action = "Wähle Aktionskarte aus."
                        self.this_player_card_selection.append(self.this_player_cards.index(c))
                        self.draw_card_highlight([self.this_player_cards.index(c)], "#00ff00", "actioncard")
            if self.this_player_turns['sender'] == "CARD":
                self.this_player_turns['sender'] = "BTN"  # set card as btn
                self.this_player_turns['turn'] = self.this_player_cards[self.this_player_turns['card']]
        # --- 48 - ACTIONCARD - Prognose ----------------------------------------------------------------------------- #
        if self.this_player_turns['turn'] == 48:
            if self.this_player_turns['sender'] == "BTN":  # initialize action
                print("ACTION PROGNOSE")
        # --- 49 - ACTIONCARD - Freiflug ----------------------------------------------------------------------------- #
        if self.this_player_turns['turn'] == 49:
            if self.this_player_turns['sender'] == "BTN":  # initialize action
                print("ACTION FREIFLUG")
        # --- 50 - ACTIONCARD - zähle Bevölkerung -------------------------------------------------------------------- #
        if self.this_player_turns['turn'] == 50:
            if self.this_player_turns['sender'] == "BTN":  # initialize action
                self.draw_card_highlight(None)
                self.this_player_card_selection = []
                self.txt_action = "Lade Städte..."

                self.value = {'v': self.localversion,
                              'player': self.this_player_num}
                self._update('get_inf_disposal')
        # --- 51 - ACTIONCARD - staatliche Subvention ---------------------------------------------------------------- #
        if self.this_player_turns['turn'] == 51:
            if self.this_player_turns['sender'] == "BTN":  # initialize action
                print("ACTION SUBVENTION")
        # --- 52 - ACTIONCARD - ruhige Nacht ------------------------------------------------------------------------- #
        if self.this_player_turns['turn'] == 52:
            if self.this_player_turns['sender'] == "BTN":  # initialize action
                print("ACTION RUHIGE NACHT")
        # endregion

        if self.game_STATE == "PASSIV":  # awaits turn
            if self.current_player == self.this_player_num:  # init STATE: action
                self.this_player_turns["turns_left"] = 4
                self.this_player_turns['turn'] = 0
                self.txt_action = "Du bist am Zug."
                self.game_STATE = "ACTION"
            else:
                self.txt_status = self.all_player_name[self.current_player] + " ist am Zug."
            # ------ exchange card ----------------------------------------------------------------------------------- #
            if len(self.this_player_drawcards) > 0 and self.this_player_turns['sender'] == "CARD":

                playercard_decline = []
                playercard_burn = []

                if self.this_player_turns['card'] < len(self.this_player_cards):  # replace card
                    playercard_burn.append(self.this_player_cards[self.this_player_turns['card']])
                elif self.this_player_turns['card'] == 7:  # decline card
                    playercard_decline.append(self.this_player_drawcards[0])

                del self.this_player_drawcards[0]
                self.gameupdatelist['cards'].append(7)

                self.value = {'v': self.localversion,
                              'status':     "response",
                              'exchange':   self.this_player_exchange,
                              'decline':    playercard_decline,
                              'burn':       playercard_burn}
                self._update('card_exchange')

        if self.game_STATE == "ACTION":
            # awaits click to set action, execute action, STATE ends when turns_left = 0
            if self.this_player_turns["turns_left"] > 0:
                # region ###### set statustext ######
                if self.this_player_turns["turns_left"] > 1:
                    self.txt_status = "Aktionsphase: " + str(self.this_player_turns["turns_left"]) + \
                                      " Aktionen verbleibend."
                else:
                    self.txt_status = "Aktionsphase: Eine Aktion verbleibend."
                # endregion
                # region ###### actions ######
                # ---  3 - build center ------------------------------------------------------------------------------ #
                if self.this_player_turns['turn'] == 3:
                    if self.this_player_turns['sender'] != "":
                        # init var
                        pos = self.all_player_pos[self.this_player_num]
                        center = []
                        for anz, c in enumerate(self.city):
                            if c.get("c"):
                                center.append(anz)

                        if pos in self.this_player_cards or \
                                self.all_player_role[self.this_player_num] == 7:  # betriebsexperte

                            if self.city[pos]['c'] != 1:
                                if len(center) < 6:  # build new center
                                    # update game
                                    self.this_player_turns['turns_left'] -= 1
                                    # update server

                                    self.value = {'v': self.localversion,
                                                  'player': self.this_player_num,
                                                  'center_new': pos,
                                                  'center_removed': None,
                                                  'cards': self.this_player_cards}
                                    self._update('center')
                                else:  # move existing center
                                    if self.this_player_turns['sender'] == "BTN":  # highlight for movement
                                        self.draw_city_highlight(center)
                                        self.txt_action = "Wähle Center zum verschieben"
                                    if self.this_player_turns['sender'] == "CITY":  # move center
                                        # update game
                                        self.this_player_turns['turns_left'] -= 1
                                        # update server
                                        self.value = {'v': self.localversion,
                                                      'player': self.this_player_num,
                                                      'center_new': pos,
                                                      'center_removed': self.this_player_turns['city'],
                                                      'cards': self.this_player_cards}
                                        self._update('center')
                            else:
                                self.txt_action = "Nur ein Forschungscenter möglich."
                        else:
                            self.txt_action = "Stadtkarte benötigt"
                # ---  4 - cure disease ------------------------------------------------------------------------------ #
                if self.this_player_turns['turn'] == 4:
                    if self.this_player_turns['sender'] == "BTN":
                        check = 0
                        dis = None
                        for c in range(0, 4):
                            if self.city[self.all_player_pos[self.this_player_num]]['i'][c] > 0:
                                check += 1
                                dis = c
                        if check == 0:
                            self.txt_action = "Keine Krankheit zu behandeln."
                        elif check == 1:
                            # only 1 disease in city
                            # update game
                            self.this_player_turns['turns_left'] -= 1
                            # update server
                            self.value = {'v': self.localversion,
                                          'player': self.this_player_num,
                                          'disease': dis}
                            self._update('update_inf')
                        else:
                            # several diseases, select wich to cure
                            self.draw_disease_selection(self.all_player_pos[self.this_player_num])
                    if self.this_player_turns['sender'] == "DIS_":
                        # update game
                        self.draw_disease_selection()
                        self.this_player_turns['turns_left'] -= 1
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.this_player_num,
                                      'disease': self.this_player_turns['disease']}
                        self._update('update_inf')
                # ---  5 - share knowledge --------------------------------------------------------------------------- #
                if self.this_player_turns['turn'] == 5:
                    # region ###### info ######
                    # A player has citycard
                    # B other player in same city has citycard
                    # C player is role 4
                    # D other player in same city is role 4
                    #
                    # A, C, AC  ->  send only
                    # B, D, BD	->  get only
                    # AD, BC    ->	send + get
                    # endregion

                    def execute_change():
                        if self.check_exchange(self.this_player_exchange['sender'],
                                               self.this_player_exchange['receiver'],
                                               self.this_player_exchange['card']):
                            self.txt_action = "Warte auf Bestätigung"
                            self.this_player_exchange['status'] = "request"

                            self.value = {'v':      self.localversion}
                            for item in self.this_player_exchange:
                                self.value[item] = self.this_player_exchange[item]
                            self._update('card_exchange')
                        else:
                            self.txt_action = "ERROR exchange"
                            print("ERROR exchange")
                            self.report_error("Player " + str(self.this_player_num) + " ERROR exchange")

                        # update game
                        self.this_player_card_selection = []
                        self.draw_card_highlight(None)
                        self.draw_player_selection()

                    if self.this_player_turns['sender'] == "BTN":

                        self.this_player_card_selection = []
                        self.exchange = []  # reset exchange state
                        self.this_player_exchange = {'status': "", 'sender': None, 'receiver': None, 'card': None}

                        player = []  # get all players in city of current player
                        for num, p in enumerate(self.all_player_pos):
                            if p == self.all_player_pos[self.this_player_num]:
                                player.append(num)

                        if len(player) > 1:
                            # region build exchange option
                            for p in player:
                                if self.all_player_role[p] == 4:  # forscherin
                                    if self.this_player_num == p:
                                        self.exchange.append("C")
                                    else:
                                        self.exchange.append("D")
                                if self.all_player_pos[self.this_player_num] in self.all_player_cards[p]:
                                    if self.this_player_num == p:
                                        self.exchange.append("A")
                                    else:
                                        self.exchange.append("B")
                            # highlight option
                            send_c = []  # collect all cards that possible can be send
                            if self.all_player_role[self.this_player_num] == 4:  # forscherin
                                for num, c in enumerate(self.this_player_cards):
                                    if c < 48:
                                        send_c.append(num)
                                        if "C" not in self.exchange:
                                            self.exchange.append("C")

                            for num, c in enumerate(self.this_player_cards):
                                if self.all_player_pos[self.this_player_num] == c:
                                    if num not in send_c:
                                        send_c.append(num)
                                    if "A" not in self.exchange:
                                        self.exchange.append("A")

                            get_c = []  # collect all players that are able to share cards (send)
                            for p in player:
                                if p != self.this_player_num:
                                    if self.all_player_role[p] == 4:  # forscherin
                                        for c in self.all_player_cards[p]:
                                            if c < 48 and p not in get_c:
                                                if "D" not in self.exchange:
                                                    self.exchange.append("D")
                                                get_c.append(p)
                                    elif self.all_player_pos[self.this_player_num] in self.all_player_cards[p]:
                                        if p not in get_c:
                                            get_c.append(p)
                                        if "B" not in self.exchange:
                                            self.exchange.append("B")

                            # if player has cards to send, add all other players to list as receivers
                            if len(send_c) > 0:
                                for p in player:
                                    if p != self.this_player_num and p not in get_c:
                                        get_c.append(p)

                            # if player can send and receive, add this.player to playerselection
                            if ("A" in self.exchange and "D" in self.exchange) \
                                    or ("B" in self.exchange and "C" in self.exchange):
                                get_c.append(self.this_player_num)
                            # endregion

                            # draw selection options
                            self.draw_card_highlight(send_c, "#ff0000")
                            self.draw_player_selection(get_c)

                            if ("A" in self.exchange or "C" in self.exchange) \
                                    and not ("B" in self.exchange and "D" in self.exchange):
                                # send cards only
                                self.this_player_exchange['sender'] = self.this_player_num
                                self.txt_action = "Wähle Karte und Empfänger aus"
                            elif ("B" in self.exchange or "D" in self.exchange) \
                                    and not ("A" in self.exchange and "C" in self.exchange):
                                # receive only
                                self.this_player_exchange['receiver'] = self.this_player_num
                                self.txt_action = "Wähle Kartengeber aus"
                            elif ("A" in self.exchange and "D" in self.exchange) \
                                        or ("B" in self.exchange and "C" in self.exchangec):
                                # send and receive
                                self.txt_action = "Wähle Empfänger und/oder Karte zum geben aus"
                        else:
                            self.txt_action = "Kein anderer Spieler in deiner Stadt."

                    if self.this_player_turns['sender'] == "CARD":
                        c_num = self.this_player_turns['card']
                        if c_num in self.this_player_card_selection:
                            self.this_player_card_selection.remove(c_num)
                            self.draw_card_highlight([c_num], "#ff0000")
                        else:
                            self.this_player_card_selection.append(c_num)
                            self.draw_card_highlight([c_num], "#00ff00")

                        if len(self.this_player_card_selection) == 1:
                            # send cards only
                            self.this_player_exchange['sender'] = self.this_player_num
                            self.this_player_exchange['card'] = self.this_player_cards[c_num]
                            if self.this_player_exchange['receiver'] is None:
                                self.txt_action = "Wähle Empfänger aus"  # select receiver
                            else:
                                execute_change()

                    if self.this_player_turns['sender'] == "PLAY":
                        selected_player = self.this_player_turns['player']

                        if ("A" in self.exchange or "C" in self.exchange) \
                                and not ("B" in self.exchange and "D" in self.exchange):
                            # send cards only
                            self.this_player_exchange['receiver'] = selected_player
                            if self.this_player_exchange['card'] is None:
                                self.txt_action = "Wähle Karte aus."  # select card
                                self.draw_player_selection()
                            else:
                                execute_change()
                        elif ("B" in self.exchange or "D" in self.exchange) \
                                and not ("A" in self.exchange and "C" in self.exchange):
                            self.this_player_exchange['sender'] = selected_player
                            self.draw_player_selection()
                            execute_change()
                        elif ("A" in self.exchange and "D" in self.exchange) \
                                or ("B" in self.exchange and "C" in self.exchangec):
                            if selected_player == self.this_player_num:
                                # player is receiver
                                self.this_player_exchange['receiver'] = selected_player
                                self.draw_player_selection()
                                execute_change()
                            else:
                                # player is sender
                                self.this_player_exchange['sender'] = selected_player
                                if self.this_player_exchange['card'] is None:
                                    self.txt_action = "Wähle Karte aus."  # select card
                                    self.draw_player_selection()
                                else:
                                    execute_change()
                # ---  6 - healing ----------------------------------------------------------------------------------- #
                if self.this_player_turns['turn'] == 6:
                    if self.this_player_turns['sender'] == "BTN":
                        if self.city[self.all_player_pos[self.this_player_num]].get("c"):
                            self.this_player_card_selection = []
                            check = [0, 0, 0, 0]
                            for c in self.this_player_cards:
                                if c <= 47:
                                    check[self.city[c].get("d")] += 1
                            for idf, f in enumerate(check):
                                if f > 4 or (self.all_player_role[self.this_player_num] == 1 and f > 3):
                                    if self.healing[idf] == 0:
                                        selection = []
                                        for idc, c in enumerate(self.this_player_cards):
                                            if self.city[c].get("d") == idf:
                                                selection.append(idc)

                                        # self.this_player_turns['target'] = idf
                                        if self.all_player_role[self.this_player_num] == 1:
                                            self.txt_action = "Wähle 4 Karten aus."
                                        else:
                                            self.txt_action = "Wähle 5 Karten aus."
                                        self.draw_card_highlight(selection, "#ff0000")
                                        break
                                    else:
                                        self.txt_action = "Heilmittel bereits erforscht"
                                else:
                                    self.txt_action = "Nicht genug Karten von einer Farbe"
                        else:
                            self.txt_action = "Forschungscenter benötigt"
                    if self.this_player_turns['sender'] == "CARD":
                        c_num = self.this_player_turns['card']
                        if c_num in self.this_player_card_selection:
                            self.this_player_card_selection.remove(c_num)
                            self.draw_card_highlight([c_num], "#ff0000")
                        else:
                            self.this_player_card_selection.append(c_num)
                            self.draw_card_highlight([c_num], "#00ff00")

                        required = 4 if self.all_player_role[self.this_player_num] == 1 else 5

                        if len(self.this_player_card_selection) < required:
                            self.txt_action = str(len(self.this_player_card_selection)) + "/" + \
                                              str(required) + " Karten ausgewählt"
                        else:
                            self.txt_action = "Heilmittel entdeckt."
                            # update game
                            self.this_player_turns['turns_left'] -= 1
                            # update server
                            remove_cards = []
                            for c in self.this_player_card_selection:
                                remove_cards.append(self.this_player_cards[c])
                            self.value = {'v': self.localversion,
                                          'player': self.this_player_num,
                                          'cards': remove_cards}
                            self.this_player_card_selection = []
                            self._update('heal')
                # --- 11 - move -------------------------------------------------------------------------------------- #
                if self.this_player_turns['turn'] == 11:
                    if self.this_player_turns['sender'] == "BTN":  # initialize action
                        self.get_player_path()
                        self.draw_city_highlight(self.this_player_range)
                        self.txt_action = "Bewegen: Wähle Ziel. (keine Karte notwendig)"
                    if self.this_player_turns['sender'] == "CITY":  # do action
                        self.draw_city_highlight()
                        self.this_player_turns['turns_left'] -= self.this_player_turns['steps']
                        self.txt_action = ""
                        move_player = self.logistician if self.logistician < 3 else self.this_player_num
                        self.logistician = 5
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.this_player_num,
                                      'path': self.get_player_path(self.this_player_turns['city']),
                                      'moveplayer': move_player,
                                      'moveto': self.this_player_turns['city'],
                                      'usedcards': []}
                        self._update('player_move')
                # --- 12 - fly direct -------------------------------------------------------------------------------- #
                if self.this_player_turns['turn'] == 12:
                    if self.this_player_turns['sender'] == "BTN":  # initialize action
                        self.draw_city_highlight(self.this_player_cards)
                        self.txt_action = "Direktflug: Wähle Ziel. (eine Karte wird benötigt)"
                    if self.this_player_turns['sender'] == "CITY":  # do action
                        self.draw_city_highlight()
                        self.this_player_turns['turns_left'] -= 1
                        self.txt_action = ""
                        move_player = self.logistician if self.logistician < 3 else self.this_player_num
                        self.logistician = 5
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.this_player_num,
                                      'moveplayer': move_player,
                                      'moveto': self.this_player_turns['city'],
                                      'usedcards': [self.this_player_turns['city']]}
                        self._update('player_move')
                # --- 13 - fly charter ------------------------------------------------------------------------------- #
                if self.this_player_turns['turn'] == 13:
                    if self.this_player_turns['sender'] == "BTN":  # initialize action
                        if self.logistician < 3:
                            pos = self.all_player_pos[self.logistician]
                        else:
                            pos = self.all_player_pos[self.this_player_num]

                        if pos in self.this_player_cards:
                            self.txt_action = "Charterflug: Wähle Zielstadt."
                            allcitys = [x for x in range(48)]
                            allcitys.remove(pos)
                            self.draw_city_highlight(allcitys)
                        else:
                            self.draw_city_highlight()
                            self.txt_action = "Charterflug nicht möglich. (Karte vom Standort wird benötigt)"
                    if self.this_player_turns['sender'] == "CITY":  # do action
                        self.draw_city_highlight()
                        self.this_player_turns['turns_left'] -= 1
                        self.txt_action = ""
                        move_player = self.logistician if self.logistician < 3 else self.this_player_num
                        self.logistician = 5
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.this_player_num,
                                      'moveplayer': move_player,
                                      'moveto': self.this_player_turns['city'],
                                      'usedcards': [self.all_player_pos[move_player]]}
                        self._update('player_move')
                # --- 14 - fly special ------------------------------------------------------------------------------- #
                if self.this_player_turns['turn'] == 14:
                    if self.this_player_turns['sender'] == "BTN":  # initialize action
                        if self.city[self.all_player_pos[self.this_player_num]]['c']:
                            self.txt_action = "Sonderflug: Wähle Zielstadt mit Forschungscenter."
                            citys = []
                            for c in self.city:
                                if c['c']:
                                    citys.append(c['ID'])
                            citys.remove(self.all_player_pos[self.this_player_num])
                            self.draw_city_highlight(citys)
                        else:
                            self.draw_city_highlight()
                            self.txt_action = "Sonderflug nicht möglich. (Forschungszentrum benötigt)"
                    if self.this_player_turns['sender'] == "CITY":  # do action
                        self.draw_city_highlight()
                        self.this_player_turns['turns_left'] -= 1
                        self.txt_action = ""
                        move_player = self.logistician if self.logistician < 3 else self.this_player_num
                        self.logistician = 5
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.this_player_num,
                                      'moveplayer': move_player,
                                      'moveto': self.this_player_turns['city'],
                                      'usedcards': []}
                        self._update('player_move')
                # --- 15 - LOGISTIKER - select player ---------------------------------------------------------------- #
                if self.this_player_turns['turn'] == 15:
                    if self.this_player_turns['sender'] == "BTN":  # initialize action
                        self.draw_city_highlight()
                        selected_player = []
                        for num, name in enumerate(self.all_player_name):
                            if name != '':
                                selected_player.append(num)
                        self.draw_player_selection(selected_player, "LOG")
                        self.txt_action = "Wähle zu bewegenden Spieler"
                    if self.this_player_turns['sender'] == "PLAY":  # get player
                        self.draw_player_selection()
                        self.logistician = self.this_player_turns['player']
                        self.txt_action = "Bewege " + self.all_player_name[self.logistician]
                # --- 16 - LOGISTIKER - move player to player -------------------------------------------------------- #
                if self.this_player_turns['turn'] == 16:
                    if self.this_player_turns['sender'] == "BTN":  # initialize action
                        self.draw_city_highlight()
                        selected_player = []
                        for num, name in enumerate(self.all_player_name):
                            if name != '':
                                selected_player.append(num)
                        self.draw_player_selection(selected_player, "LOG")
                        self.txt_action = "Wähle zu bewegenden Spieler"

                    if self.this_player_turns['sender'] == "PLAY":  # get player
                        self.draw_player_selection()

                        selected_city = []
                        for num, name in enumerate(self.all_player_name):
                            if name != '':
                                selected_city.append(self.all_player_pos[num])
                        selected_city.remove(self.all_player_pos[self.this_player_turns['player']])

                        self.draw_city_highlight(selected_city)
                        self.txt_action = "Spezialfähigkeit: Wähle Zielstadt"

                    if self.this_player_turns['sender'] == "CITY":  # get city and execute
                        self.draw_city_highlight()
                        self.this_player_turns['turns_left'] -= 1
                        self.txt_action = ""
                        self.logistician = 5
                        # update server
                        self.value = {'v': self.localversion,
                                      'player': self.this_player_num,
                                      'moveplayer': self.this_player_turns['player'],
                                      'moveto': self.this_player_turns['city'],
                                      'usedcards': []}
                        self._update('player_move')
                # --- 32 - end turn ---------------------------------------------------------------------------------- #
                if self.this_player_turns['turn'] == 32 and self.this_player_turns['sender'] == "BTN":
                    self.this_player_turns = {'sender': "", 'turn': 99, 'turns_left': 0}
                    self.txt_action = ""
                    self.game_STATE = "SUPPLY"
                # endregion
            else:  # ACTION is over start next STATE
                # remove all highlights
                self.draw_city_highlight()
                self.draw_disease_selection()

                self.this_player_turns["turn"] = 99
                self.txt_action = ""
                self.game_STATE = "SUPPLY"

        if self.game_STATE == "SUPPLY":
            # awaits click on cards, execute supply, STATE ends when draw_cards = 0
            if len(self.this_player_drawcards) > 0 or self.this_player_turns["turn"] >= 100:
                # region ###### set statustext ######
                if self.this_player_drawcards[0] != self.card_epidemie:
                    if len(self.this_player_drawcards) > 1:
                        self.txt_status = "Nachschubphase: 2 Karten ziehen"
                    else:
                        self.txt_status = "Nachschubphase: 1 Karten ziehen"
                    if self.this_player_turns["turn"] >= 100:
                        self.txt_status = "Infizieren."
                else:
                    self.txt_status = "Epidemie auslösen."
                # endregion
                # region ###### actions ######
                # --- drawcard --------------------------------------------------------------------------------------- #
                if self.this_player_drawcards[0] != self.card_epidemie and self.this_player_turns["turn"] < 100:
                    if self.this_player_turns['sender'] == "CARD":
                        playercard_add = []
                        playercard_remove = []
                        playercard_switch = []
                        playercard_burn = []
                        if 7 > self.this_player_turns['card'] >= len(self.this_player_cards):  # add card to player
                            playercard_add.append(self.this_player_drawcards[0])
                        elif self.this_player_turns['card'] == 7:  # dismiss card
                            playercard_burn.append(self.this_player_drawcards[0])
                        else:  # replace card
                            playercard_switch.append((self.this_player_cards[self.this_player_turns['card']],
                                                      self.this_player_drawcards[0]))

                        del self.this_player_drawcards[0]
                        self.gameupdatelist['cards'].append(7)

                        # update server
                        self.value = {'player': self.this_player_num,
                                      'add': playercard_add,
                                      'remove': playercard_remove,
                                      'switch': playercard_switch,
                                      'burn': playercard_burn}
                        self._update('update_cards')
                # --- epidemie --------------------------------------------------------------------------------------- #
                else:
                    # start epidemie and draw infection card
                    if self.this_player_turns["turn"] == 0 and self.this_player_turns['sender'] == "CARD":
                        print(">>> EPIDEMIE >>>", str(self.this_player_drawcards))
                        self.game_canvas.itemconfigure(self.i_quicktip, fill="")
                        self.txt_action = ""
                        self.this_player_turns["turn"] = 100
                        del self.this_player_drawcards[0]
                        print(">>> EPIDEMIE >>>", str(self.this_player_drawcards))
                        self.this_player_turns['sender'] = ""
                        self._update('draw_epidemiecard')
                    # infect city
                    if self.this_player_turns["turn"] == 100 and self.this_player_turns['sender'] == "CARD":
                        print("zug")
                        inf_card = self.this_player_drawcards[0]
                        del self.this_player_drawcards[0]
                        self.gameupdatelist['cards'].append(7)
                        self.this_player_turns["turn"] = 0
                        # update server -> do calculation online
                        self.value = {'v': self.localversion,
                                      'card': inf_card,
                                      'epidemie': True}
                        self._update('update_inf')
                # endregion
            else:
                # INIT SUPPLY with drawing cards
                if self.this_player_turns["turn"] == 99:
                    self.this_player_turns["turn"] = 0
                    self._update('draw_playercard')
                # SUPPLY is over start next STATE
                else:
                    self.this_player_turns["turn"] = 999
                    self.txt_action = ""
                    self.game_canvas.itemconfigure(self.i_quicktip, fill="")
                    self.game_STATE = "INFECT"

        if self.game_STATE == "INFECT":
            # awaits click on cards, execute supply, STATE ends when draw_cards = 0
            if len(self.this_player_drawcards) > 0:
                # region ###### set statustext ######
                self.txt_action = "Infiziere Stadt"
                # endregion
                # region ###### actions ######
                if self.this_player_turns['sender'] == "CARD":
                    inf_card = self.this_player_drawcards[0]
                    del self.this_player_drawcards[0]
                    self.gameupdatelist['cards'].append(7)

                    # update server -> do calculation online
                    self.value = {'v': self.localversion,
                                  'card': inf_card}
                    self._update('update_inf')
                # endregion
            else:
                # INIT INFECT with drawing cards
                if self.this_player_turns["turn"] == 999:
                    self.this_player_turns["turn"] = 0
                    self._update('draw_infcard')
                # INFECT is over start next STATE -> next player
                else:
                    self.this_player_turns = {'sender': "", 'turn': 0, 'turns_left': 0}
                    self.txt_action = ""
                    self.txt_status = ""
                    self.game_canvas.itemconfigure(self.i_quicktip, fill="")
                    self.game_STATE = "PASSIV"
                    self.value = {'v': self.localversion,
                                  'player_num': self.this_player_num}
                    self._update('turn_over')

        # endregion

        # --- reset sender ----------------------------------------------------------------------------------- #
        self.this_player_turns['sender'] = ""
        # update game if necessary
        if self.game_STATE != 'INIT' and self.game_STATE != 'WAIT':
            self.game_show()

    def game_click(self, event, *args):
        if not self.block_request:
            # region ###### CLICK @ CARDS ##############################################################################
            if 8 < event.y < self.section_card:  # cardsection
                card_num = math.floor(float(event.x) / (self.section_game_w / 8))
                _print("clicked at Card: " + str(card_num))
                self.this_player_turns['sender'] = "CARD"
                self.this_player_turns['card'] = card_num

            # endregion
            # region ###### CLICK @ FIELD ##############################################################################
            elif self.section_field > event.y > self.section_card + 8:  # map -> find city

                sender = str(args[0][:4])
                if sender == "CITY":  # clicked on city
                    mycitynum = int(args[0][4:])
                    mycity = self.city[mycitynum].get("name")
                    _print("clicked at City: " + mycity)
                    self.this_player_turns['city'] = mycitynum
                    self.this_player_turns['steps'] = len(self.get_player_path(mycitynum))

                if sender == "DIS_":  # clicked on disease-selection
                    self.this_player_turns['disease'] = int(args[0][4:])

                if sender == "PLAY":  # clicked on disease-selection
                    self.this_player_turns['player'] = int(args[0][4:])

                self.this_player_turns['sender'] = sender
            # endregion
            # region ###### CLICK @ BAR/BTN ############################################################################
            elif event.y > self.section_field + 8:
                posx = self.game_canvas.coords(tk.CURRENT)[0] + event.widget.winfo_width() / 68
                num = math.floor(float(posx) / self.section_game_w * 34)
                _print("action-BTN", str(num), "clicked.")

                # reset highlights and info TODO add more / check
                self.draw_card_highlight(None)
                self.draw_card_highlight()
                self.draw_city_highlight()
                self.txt_action = ""

                if (self.this_player_turns['turns_left'] > 0 and self.game_STATE == "ACTION") or num == 7:
                    self.this_player_turns['turn'] = num
                    self.this_player_turns['sender'] = "BTN"
                else:
                    if self.this_player_turns['turns_left'] <= 0:
                        self.txt_action = "keine Züge vorhanden"
                    else:
                        self.txt_action = "Du bist nicht am Zug."
            # endregion

            self._update()

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
        self.all_player_role = args.get("player_role")

        for p in range(0, 4):
            self.lbl_player_name[p].configure(text=self.all_player_name[p])
            self.lbl_player_func[p].configure(text=get_role_name(self.all_player_role[p]))
            if args.get("player_rdy")[p] == 1:
                self.lbl_player_rdy[p].configure(text="P", font=("Wingdings 2", 16, 'bold'), fg="#006600")

        return 'getVersion'

    def game_init_player_set(self, args):
        _print()

        # playernum
        self.this_player_num = args.get("player_num")  # [0..4]
        print("player_set: thisplayer_num:", str(self.this_player_num))

        # player_name / player role
        self.all_player_role = args.get("player_role")
        self.all_player_name = args.get("player")

        if self.this_player_num > 3:
            print("to many players")
            self.lbl2.configure(text="Zu viele Spieler")
        else:
            self.btn_start.configure(state=NORMAL)

            self.role_image.configure(image=self.img_char[self.all_player_role[self.this_player_num]])

        return self.game_init_update(args)

    def game_init_recon(self, args):
        _print()
        self.localversion = 0  # -> force update after recon
        self.all_player_name = args.get("player")
        self.all_player_role = args.get("player_role")
        self.game_STATE = args.get("state")
        self.game_STATE = "WAIT"

        return self.game_init_execute_game()

    def game_init_execute_game(self):
        if self.game_STATE == "WAIT":
            _print()
            self.PREPframe.destroy()

            self.title("Pandemie")  # region UI

            user32 = ctypes.windll.user32
            # screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            # print(str(user32.GetSystemMetrics(0)) + "x" + str(user32.GetSystemMetrics(1)))
            win_x = user32.GetSystemMetrics(0) - 20
            win_y = user32.GetSystemMetrics(1) - 60

            if AM_DEBUG_OUTPUT:
                win_x = int(win_x / 2)
                win_y = int(win_y / 2)
                if self.this_player_num == 0:
                    self.geometry(str(win_x) + 'x' + str(win_y) + '+1280+2')
                elif self.this_player_num == 1:
                    self.geometry(str(win_x) + 'x' + str(win_y) + '+1280+780')
                elif self.this_player_num == 2:
                    self.geometry(str(win_x) + 'x' + str(win_y) + '+1+2')
                elif self.this_player_num == 3:
                    self.geometry(str(win_x) + 'x' + str(win_y) + '+1+780')
            else:
                self.geometry(str(win_x) + 'x' + str(win_y) + '+2+2')

            # self.display_game(None)
            self.lbl_empty.place(relx=0.5, rely=0.5, anchor=CENTER)

            self.game_STATE = 'PASSIV'
            self.value = {'v': 0}
        return 'get_update'
    # endregion

    # region ------ MAINGAME -------------------------------------------------------------------------------------------
    def game_lose(self):
        self.game_STATE = "LOSE_GAME"
        self.config(cursor="pirate")
        _print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>   You lose.")

        s = int(self.winfo_height() * 0.66)

        self.img_lose = ImageTk.PhotoImage(self.img_lose_raw.resize((s, s), Image.ANTIALIAS))
        self.game_canvas.create_image(
            int(self.section_game_w / 2), int(self.winfo_height() / 2),
            image=self.img_lose,
            anchor=CENTER)

        self.running = False
        return 'get_version'

    def game_win(self):
        self.game_STATE = "WIN_GAME"
        self.config(cursor="heart")
        _print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>   You win.")

        s = int(self.winfo_height() * 0.66)

        self.img_win = ImageTk.PhotoImage(self.img_win_raw.resize((s, s), Image.ANTIALIAS))
        self.game_canvas.create_image(
            int(self.section_game_w / 2), int(self.winfo_height() / 2),
            image=self.img_win,
            anchor=CENTER)

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
            aktpos = self.all_player_pos[self.this_player_num]
        else:
            aktpos = self.all_player_pos[self.logistician]
            print(aktpos)

        # get distance to specific city
        if len(args) > 0:
            target = args[0]
            path = [target]
            while get_pre(aktpos, target) != aktpos:
                path.append(get_pre(aktpos, target))
                target = get_pre(aktpos, target)
            return path
        # update this_player_range
        else:
            self.this_player_range = [aktpos]
            for r in range(0, self.this_player_turns['turns_left']):
                step = []
                for n in self.this_player_range:
                    for a in self.city[n].get('con'):
                        append = True
                        for check in step:
                            if check == a:
                                append = False
                        if append:
                            step.append(a)
                for s in step:
                    append = True
                    for check in self.this_player_range:
                        if check == s:
                            append = False
                    if append:
                        self.this_player_range.append(s)
            self.this_player_range.remove(aktpos)

    def receive_card(self, *args):
        _print(args)
        # get args from response
        if len(args) > 0:
            if 'new_cards' in args[0] and self.game_STATE == "SUPPLY":
                self.this_player_drawcards = args[0]['new_cards']
                self.txt_status = "Nachschubphase"

            if 'new_epi' in args[0] and self.game_STATE == "SUPPLY":
                old = self.this_player_drawcards
                self.this_player_drawcards = [args[0]['new_epi'][0]]
                for o in old:
                    self.this_player_drawcards.append(o)
                self.txt_status = "Epidemie"
                print(">>> EPIDEMIE >>>", str(self.this_player_drawcards))

            if 'new_inf' in args[0] and self.game_STATE == "INFECT":
                self.this_player_drawcards = args[0]['new_inf']
                self.txt_status = "Infektionsphase"

            self.gameupdatelist['cards'].append(7)

        return 'getVersion'

    def check_exchange(self, sender, receiver, card):
        fail = False

        # fill empty fields with existing variables if existant
        if sender is None:
            sender = self.this_player_exchange['sender']
        if receiver is None:
            receiver = self.this_player_exchange['receiver']
        if card is None:
            card = self.this_player_exchange['card']

        # sender must have citycard or be role 4
        if sender is not None:
            if self.all_player_role[sender] != 4 \
                    and self.all_player_pos[sender] not in self.all_player_cards[sender]:
                fail = True

        # receiver must be in same city as sender
        if sender is not None and receiver is not None:
            if self.all_player_pos[sender] != self.all_player_pos[receiver]:
                fail = True

        # card must be citycard or sender is role 4
        if card is not None and sender is not None:
            if self.all_player_role[sender] != 4 and card not in self.all_player_cards[sender]:
                fail = True

        return not fail

    def exchange_card(self, card_exchange):
        _print()

        # card_exchange = {'status': "request", 'sender': 2, 'card': 2, 'receiver': 0}

        # update only when new request
        if self.this_player_exchange != card_exchange:
            self.this_player_exchange = card_exchange
            # check if player is participant
            if card_exchange['sender'] == self.this_player_num and self.game_STATE == "PASSIV":
                print("player is sender")
                self.txt_action = str(self.all_player_name[card_exchange['sender']]) + \
                                  " möchte eine Karte von dir haben"
                for num, c in enumerate(self.this_player_cards):
                    if self.check_exchange(self.this_player_num,
                                           card_exchange['receiver'],
                                           c):
                        self.this_player_card_selection.append(num)
                        self.draw_card_highlight([num], "#00ff00")
            elif card_exchange['receiver'] == self.this_player_num:
                print("player is receiver")
                self.txt_action = "Du erhältst eine Karte von " + str(self.all_player_name[card_exchange['sender']])
                self.this_player_drawcards.append(card_exchange['card'])
                self.gameupdatelist['cards'].append(7)
                self.draw_card_highlight()
            elif card_exchange['sender'] is None and card_exchange['receiver'] is None \
                    and self.game_STATE == "PASSIV":
                self.txt_status = self.all_player_name[self.current_player] + " ist am Zug."

        # remove highlight
        # self.draw_card_highlight(None)

    def action_count_population(self, args):
        selection = args['inf_disposal']
        self.draw_city_highlight(selection, "#ff00ff")
        self.txt_action = "Wähle zu entfernende Stadtkarte aus"
        return 'getVersion'

    def report_error(self, error):
        _print(error)
        self.value = {'v': self.localversion,
                      'e': error}
        self._update('error')
    # endregion

    # region ###### DRAW ###############################################################################################
    def game_update(self, args):
        _print()

        if 'city' in args:
            for num, c in enumerate(args.get("city")):
                akt_c = self.city[num]['i'], self.city[num]['c']
                if akt_c != ([c[0], c[1], c[2], c[3]], c[4]):
                    self.city[num]['i'][0] = c[0]
                    self.city[num]['i'][1] = c[1]
                    self.city[num]['i'][2] = c[2]
                    self.city[num]['i'][3] = c[3]
                    self.city[num]['c'] = c[4]
                    self.gameupdatelist['city'].append(num)

        if 'cards' in args:
            self.all_player_cards = args.get("cards")[0]
            cards = self.all_player_cards[self.this_player_num]
            if self.this_player_cards != cards:
                r = len(self.this_player_cards) if len(self.this_player_cards) < len(cards) \
                    else len(cards)
                for c in range(0, 7):
                    if c < r:
                        if self.this_player_cards[c] != cards[c]:
                            self.gameupdatelist['cards'].append(c)
                    else:
                        self.gameupdatelist['cards'].append(c)
                self.this_player_cards = cards
            self.exchange_card(args.get("cards")[1])

        if 'stats' in args:
            stats = args.get("stats")
            akt_m = self.outbreak, self.inflvl, self.supplies
            if akt_m != (stats[0], stats[1], stats[2]):
                self.outbreak = stats[0]
                self.inflvl = stats[1]
                self.supplies = stats[2]
                self.gameupdatelist['marker1'] = 1

            count = 0
            for i in range(0, 4):
                if self.infection[i] != stats[3 + i]:
                    count = 1
                self.infection[i] = stats[3 + i]
            if count > 0:
                self.gameupdatelist['marker1'] = 1

            count = 0
            for i in range(0, 4):
                if self.healing[i] != stats[7 + i]:
                    count = 1
                self.healing[i] = stats[7 + i]
            if count > 0:
                self.gameupdatelist['marker2'] = 1

        if 'player' in args:
            if self.all_player_pos != args.get('player')[0]:
                self.all_player_pos = args.get('player')[0]
                self.gameupdatelist['playerpos'] = 1
            self.current_player = args.get('player')[1]

        # update version
        self.localversion = args.get("v")

        return 'getVersion'

    def game_show(self):

        # region ###### get actual window dimension and calculate aspect-ration ######
        self.update()
        win_w = self.winfo_width()
        win_h = self.winfo_height()

        h = (5 * 8) + ((win_w - 72) / 8) / 7 * 10 + (win_w / 17 * 8) + (2 * win_w / 34)
        w = (win_h - (190 / 7)) * (476 / 337)

        if h > win_h:
            game_w = w
            game_h = win_h
        else:
            game_w = win_w
            game_h = h

        card_w = int((game_w - 72) / 8)
        card_h = int((game_w - 72) / 8 / 7 * 10)

        s_inf = 320 * game_w / (3380 * 2)  # variable for marker size (half the size)
        s_cen = s_inf * 120 / 320

        self.section_game_w = game_w
        self.section_card = card_h + 8
        self.section_field = int(self.section_game_w / 2.125) + self.section_card + 8
        self.section_action = self.section_field + int(self.section_game_w / 34) + 8
        self.section_status = self.section_action + int(self.section_game_w / 34) + 8
        # endregion

        if self.old_window_h != win_h or self.old_window_w != win_w:  # resize #########################################
            print("RESIZE WINDOW")

            for child in self.winfo_children():  # destroy all
                child.destroy()

            # set base frame over whole window
            self.game_frame = Frame(self, width=win_w, height=win_h, bg="#333")
            self.game_frame.place(relx=0.5, rely=0.5, width=win_w, height=win_h, anchor=CENTER)

            # canvas
            self.game_canvas = ResizingCanvas(self.game_frame, width=self.section_game_w, height=game_h,
                                              bg="#333", highlightthickness=0)
            self.game_canvas.pack()

            # infotext
            self.i_action = Label(self, text=self.txt_action, font="Helvetica 12", bg="#747474")
            self.i_status = Label(self, text=self.txt_status, font="Helvetica 12", bg="#747474")

            x = (1 / game_w * (game_w / 34 * 18))
            y = (1 / game_h * (self.section_field + 8 + (float(game_w) / 68)))
            self.i_action.place(relx=x, rely=y, anchor="w")

            x = (1 / game_w * (game_w / 34 * 23))
            y = (1 / game_h * (self.section_field + 16 + (float(game_w) / 68) * 3))
            self.i_status.place(relx=x, rely=y, anchor="w")

            # map
            self.img_map = ImageTk.PhotoImage(
                self.img_map_raw.resize((int(self.section_game_w), int(self.section_game_w / 2.125)), Image.ANTIALIAS))
            self.game_canvas.create_image(0, card_h + 16, image=self.img_map, anchor=NW)

            # Prepare cards/BG
            for bg in range(0, 8):
                self.game_canvas.create_rectangle(
                    am_rect(6 + (8 + card_w) * bg, 6, card_w + 4, card_h + 4), fill="#282828")

            # prepare infection graphics: scale
            for x in range(0, 4):
                for y in range(0, 4):
                    for z in range(0, 3):
                        self.img_inf[z][y][x] = ImageTk.PhotoImage(self.img_inf_raw[x][y]
                                                                   .resize((int(s_inf), int(s_inf)), Image.ANTIALIAS)
                                                                   .rotate(z * 120 + 120))
            # prepare center 120x120
            self.img_center = ImageTk.PhotoImage(self.img_center_raw.resize((int(s_cen), int(s_cen)), Image.ANTIALIAS))

            # BG statusbar
            self.game_canvas.create_rectangle(
                am_rect(0, self.section_action + 8, self.section_game_w, int(self.section_game_w / 34)),
                fill="#282828", outline='#3a3a3a')

            # prepare additional icons
            heal_w = (float(self.section_game_w) / 34) / 100 * 75
            for num in range(0, 2):
                self.img_icon[num] = ImageTk.PhotoImage(self.img_icon_raw[num].
                                                        resize((int(heal_w), int(heal_w)), Image.ANTIALIAS))
            icon_s = int((float(self.section_game_w) / 34))
            for num in range(2, 6):
                self.img_icon[num] = ImageTk.PhotoImage(self.img_icon_raw[num].
                                                        resize((icon_s, icon_s), Image.ANTIALIAS))

            # prepare player card and name
            self.img_char[self.all_player_role[self.this_player_num]] = \
                ImageTk.PhotoImage(self.img_char_raw[self.all_player_role[self.this_player_num]]
                                   .resize((card_w, card_h), Image.ANTIALIAS))

            # DRAW -----------------------------------------------------------------------------------------------------
            # player name and card
            x = 8
            y = int(self.section_field - 8)
            self.game_canvas.create_image(x, y,
                                          image=self.img_char[self.all_player_role[self.this_player_num]],
                                          anchor=SW)
            self.game_canvas.create_text(8, (y-card_h - 2),
                                         text=self.all_player_name[self.this_player_num],
                                         fill="#ffffff",
                                         anchor=SW,
                                         font=('Helvetica', 10, 'bold'))

            # cards
            for c in range(0, len(self.this_player_cards)):
                self.draw_cards(c)

            for c in range(0, 48):  # loop through citys
                self.draw_cities(c)

            self.draw_overlay_game()
            self.draw_player()
            self.draw_marker(1)
            self.draw_marker(2)
            self.draw_bar()

            # BTN
            btnx = (float(self.section_game_w) / 34)
            btny = self.section_field + 8
            btns = int((float(self.section_game_w) / 34))

            active = dict(fill="#000000", stipple=trans,
                          outline="#000000", width=1,
                          activeoutline="#00aa00", activewidth=3,
                          tags='btn')
            passiv = dict(fill="#000000", stipple=trans,
                          outline="#000000", width=1,
                          activeoutline="#aa0000", activewidth=1,
                          tags='btn')

            param = active if self.game_STATE == "ACTION" else passiv

            self.game_canvas.create_rectangle(am_rect(3 * btnx, btny, btns, btns), param)
            self.game_canvas.create_rectangle(am_rect(4 * btnx, btny, btns, btns), param)
            self.game_canvas.create_rectangle(am_rect(5 * btnx, btny, btns, btns), param)
            self.game_canvas.create_rectangle(am_rect(6 * btnx, btny, btns, btns), param)

            self.game_canvas.create_rectangle(am_rect(11 * btnx, btny, btns, btns), param)
            self.game_canvas.create_rectangle(am_rect(12 * btnx, btny, btns, btns), param)
            self.game_canvas.create_rectangle(am_rect(13 * btnx, btny, btns, btns), param)
            self.game_canvas.create_rectangle(am_rect(14 * btnx, btny, btns, btns), param)

            self.game_canvas.create_rectangle(am_rect(32 * btnx, btny, btns, btns), param)
            self.game_canvas.create_rectangle(am_rect(33 * btnx, btny, btns, btns), param)

            # optional additional icons
            if self.all_player_role[self.this_player_num] == 3:  # Krisenmanager
                self.game_canvas.create_image(8 * btnx, btny,
                                              image=self.img_icon[4],
                                              anchor=NW,
                                              tags="icon_4")
                self.game_canvas.create_rectangle(am_rect(8 * btnx, btny, btns, btns), param)

            if self.all_player_role[self.this_player_num] == 5:  # Logistiker
                self.game_canvas.create_image(15 * btnx, btny,
                                              image=self.img_icon[3],
                                              anchor=NW,
                                              tags="icon_3")
                self.game_canvas.create_rectangle(am_rect(15 * btnx, btny, btns, btns), param)

                self.game_canvas.create_image(16 * btnx, btny,
                                              image=self.img_icon[2],
                                              anchor=NW,
                                              tags="icon_2")
                self.game_canvas.create_rectangle(am_rect(16 * btnx, btny, btns, btns), param)

            self.i_quicktip = self.game_canvas.create_text(0, 0, text="", fill="", anchor=S,
                                                           font=('Helvetica', 10), tags="info")
            self.i_actiontip = self.game_canvas.create_text(0, 0, text="", fill="", anchor=NW,
                                                           font=('Helvetica', 10), tags="actiontip")

            self.game_canvas.tag_bind("btn", "<ButtonRelease-1>", self.game_click)
            self.game_canvas.tag_bind("btn", "<Enter>", self.draw_tooltip)
            self.game_canvas.tag_bind("btn", "<Leave>", self.dismiss_tooltip)

            # set variables for resize-check
            self.old_window_w = win_w
            self.old_window_h = win_h

            self.gameupdatelist = {'city': [], 'cards': [], 'marker1': 0, 'marker2': 0, 'playerpos': 0}

        else:  # only update, no resize

            for c in self.gameupdatelist['city']:
                self.draw_cities(c)
            if len(self.gameupdatelist['city']) > 0:
                self.draw_overlay_game()
                self.draw_player()

            for c in self.gameupdatelist['cards']:
                self.draw_cards(c)

            if self.gameupdatelist['playerpos'] == 1:
                self.draw_player()

            if self.gameupdatelist['marker1'] == 1:
                self.draw_marker(1)

            if self.gameupdatelist['marker2'] == 1 and not self.gameupdatelist['marker1'] == 1:
                self.draw_marker(2)

            if self.i_action['text'] != self.txt_action:
                self.i_action.configure(text=self.txt_action)
            if self.i_status['text'] != self.txt_status:
                self.i_status.configure(text=self.txt_status)

    def draw_cities(self, aw):
        def inf_value(e):
            return e['value']

        c = self.city[aw]
        self.game_canvas.delete("c" + str(c.get('ID')))
        card_h = self.section_card - 8
        s_inf = 320 * self.section_game_w / (3380 * 2)  # variable for marker size (half the size)
        s_cen = s_inf * 120 / 320

        # temporary infection item for current city
        infection = [{'i': 0, 'value': 0}, {'i': 1, 'value': 0}, {'i': 2, 'value': 0}, {'i': 3, 'value': 0}]
        for i in range(0, 4):
            infection[i]['value'] = c['i'][i]

        # sort infection (highest value first -> highest infection will be drawn on most inner ring
        infection.sort(key=inf_value, reverse=True)

        # get anchor-position of city (center)
        x = int(c.get('X') * float(int(self.section_game_w)) / 100)
        y = int(c.get('Y') * float(int(self.section_game_w / 2.125) / 100) + (card_h + 16))

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
            x = int(c.get('X') * float(int(self.section_game_w)) / 100) - int(s_cen / 120 * 82)
            y = int(c.get('Y') * float(int(self.section_game_w / 2.125) / 100) + (card_h + 16)) + int(
                s_cen / 120 * 50)
            self.game_canvas.create_image(x, y,
                                          image=self.img_center,
                                          anchor=CENTER,
                                          tags=("c" + str(c.get('ID')), "center"))
        self.gameupdatelist['city'] = []

    def draw_disease_selection(self, *cnum):
        self.game_canvas.delete("disease_selection")
        if len(cnum) > 0:  # draw selection
            c = self.city[cnum[0]]
            card_h = self.section_card - 8
            size = int(self.section_game_w / 35)

            # get anchor-position of city (center)
            x = int(c.get('X') * float(int(self.section_game_w)) / 100) + size / 2
            y = int(c.get('Y') * float(int(self.section_game_w / 2.125) / 100) + (card_h + 16)) + 15

            pos = 0
            for i in range(0, 4):
                if c.get('i' + str(i)) > 0:
                    param = dict(activeoutline="#ffffff", activewidth=2)
                    switcher = {
                        0: "#006bfd",
                        1: "#fff300",
                        2: "#189300",
                        3: "#f10000",
                    }
                    param['fill'] = switcher.get(i)
                    param['activefill'] = switcher.get(i)
                    param['outline'] = switcher.get(i)

                    diseasetag = "DIS_" + str(i)
                    param['tags'] = "disease_selection", diseasetag

                    self.game_canvas.create_oval(x + (size + 5) * pos, y - size / 2, x + (size + 5) * pos + size,
                                                 y + size / 2,
                                                 param)
                    pos += 1
                    self.game_canvas.tag_bind(diseasetag, "<ButtonRelease-1>",
                                              lambda event, t=diseasetag: self.game_click(event, t))

    def draw_player_selection(self, *args):
        self.game_canvas.delete("player_selection")
        if len(args) > 0:  # draw selection
            if len(args[0]) > 0:
                players = args[0]
                c = self.city[self.all_player_pos[players[0]]]
                card_h = self.section_card - 8
                size = int(self.section_game_w / 35)

                if len(args) <= 1:  # if second argument -> draw for logistiker
                    # get anchor-position of city (center)
                    x = int(c.get('X') * float(int(self.section_game_w)) / 100) + size / 2
                    y = int(c.get('Y') * float(int(self.section_game_w / 2.125) / 100) + (card_h + 16)) + 15
                else:
                    x = int((float(self.section_game_w) / 34) * 15)
                    y = self.section_field - size - 8

                for pos, p in enumerate(players):
                    role = self.all_player_role[p]
                    param = dict(activeoutline="#ffffff", activewidth=2)
                    switcher = {
                        1: "#d6d7df",
                        2: "#245a49",
                        3: "#52aedb",
                        4: "#8f5735",
                        5: "#cf63ae",
                        6: "#ee7024",
                        7: "#7ab851",
                    }
                    param['fill'] = switcher.get(role)
                    param['activefill'] = switcher.get(role)
                    param['outline'] = switcher.get(role)

                    playertag = "PLAY" + str(p)
                    param['tags'] = "player_selection", playertag

                    self.game_canvas.create_oval(x + (size + 5) * pos, y, x + (size + 5) * pos + size, y + size, param)

                    self.game_canvas.tag_bind(playertag, "<ButtonRelease-1>",
                                              lambda event, t=playertag: self.game_click(event, t))

    def draw_cards(self, card_num):
        self.game_canvas.delete("card" + str(card_num))

        card_w = int((self.section_game_w - 72) / 8)
        card_h = int((self.section_game_w - 72) / 8 / 7 * 10)

        # draw player card
        if card_num < len(self.this_player_cards):
            card = self.this_player_cards[card_num]
            self.img_c1[card] = ImageTk.PhotoImage(
                self.img_c1_raw[card].resize((int(card_w), int(card_h)), Image.ANTIALIAS))
            self.game_canvas.create_image(
                8 + (8 + card_w) * card_num, 8, image=self.img_c1[card], anchor=NW, tags="card" + str(card_num))

        # draw icon for actioncard
            if self.this_player_cards[card_num] > 47 and not self.actioncard:
                self.actioncard = True
                btnx = (float(self.section_game_w) / 34)
                btny = self.section_field + 8
                btns = int((float(self.section_game_w) / 34))
                self.game_canvas.create_image(7 * btnx, btny,
                                              image=self.img_icon[5],
                                              anchor=NW,
                                              tags="icon_5")
                self.game_canvas.create_rectangle(am_rect(7 * btnx, btny, btns, btns),
                                                  fill="#000000",
                                                  stipple=trans,
                                                  outline="#000000",
                                                  width=1,
                                                  activeoutline="#00aa00",
                                                  activewidth=3,
                                                  tags=('btn', "icon_5"))
        # delete action icon if no actioncard available
            check = True
            for c in self.this_player_cards:
                if c > 47:
                    check = False
            if check:
                self.game_canvas.delete("icon_5")
                self.actioncard = False

        # draw card pile
        if len(self.this_player_drawcards) > 0:  # drawcard
            if self.this_player_drawcards[0] not in self.this_player_cards:  # only resize if not in playercards
                self.img_c1[self.this_player_drawcards[0]] = ImageTk.PhotoImage(
                    self.img_c1_raw[self.this_player_drawcards[0]].resize((int(card_w), int(card_h)), Image.ANTIALIAS))
            self.game_canvas.create_image(
                8 + (8 + card_w) * 7, 8, image=self.img_c1[self.this_player_drawcards[0]], anchor=NW, tags="cards")

            # draw overlay (infect)
            if self.game_STATE == "INFECT" or self.this_player_turns["turn"] >= 100:
                self.img_c2 = ImageTk.PhotoImage(
                    self.img_c2_raw.resize((int(card_w), int(card_h)), Image.ANTIALIAS))
                self.game_canvas.create_image(
                    8 + (8 + card_w) * 7, 8, image=self.img_c2, anchor=NW, tags="cards")
        # draw back
        else:
            if self.game_STATE == "INFECT":
                self.img_c2_back = ImageTk.PhotoImage(
                    self.img_c2_back_raw.resize((int(card_w), int(card_h)), Image.ANTIALIAS))
                self.game_canvas.create_image(
                    8 + (8 + card_w) * 7, 8, image=self.img_c2_back, anchor=NW, tags="cards")
            else:
                self.img_c1[54] = ImageTk.PhotoImage(
                    self.img_c1_raw[54].resize((int(card_w), int(card_h)), Image.ANTIALIAS))
                self.game_canvas.create_image(
                    8 + (8 + card_w) * 7, 8, image=self.img_c1[54], anchor=NW, tags="cards")

        self.draw_card_highlight()
        self.gameupdatelist['cards'] = []

    def draw_bar(self):
        self.img_action = ImageTk.PhotoImage(
            self.img_action_raw.resize((int(self.section_game_w), int(self.section_game_w / 34)), Image.ANTIALIAS))
        self.game_canvas.create_rectangle(
            am_rect(0, self.section_field + 8, self.section_game_w, int(self.section_game_w / 34)),
            fill="#282828", outline='#3a3a3a')
        self.game_canvas.create_image(0, self.section_field + 8, image=self.img_action, anchor=NW, tags="action")

    def draw_player(self):
        self.game_canvas.delete("player")
        # player 80x175
        s_inf = 320 * self.section_game_w / (3380 * 2)  # variable for marker size (half the size)
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
                    x = int(c.get('X') * float(int(self.section_game_w)) / 100) \
                        - int(s_cen / 120 * 39) \
                        + int(s_cen / 120 * 52) * draw_pos
                    y = int(c.get('Y') * float(int(self.section_game_w / 2.125) / 100) + (self.section_card + 8)) \
                        - int(s_cen / 120 * 41)
                    self.game_canvas.create_image(
                        x, y, image=self.img_p[self.all_player_role[p] - 1], anchor=CENTER, tags="player")

        self.gameupdatelist['playerpos'] = 0

    def draw_marker(self, marker):
        def am_marker(xy, wh, mpos):
            return xy[0] + wh[0] * mpos[0], xy[1] + wh[1] * mpos[1], \
                   xy[0] + wh[0] * mpos[0] + wh[0], xy[1] + wh[1] * mpos[1] + wh[1]

        if marker == 1:
            self.game_canvas.delete("m1")
            # marker 1
            out_a = float(self.section_game_w) / 34 * 5, self.section_action + 8
            lvl_a = float(self.section_game_w) / 34 * 5, self.section_action + 8 + float(
                self.section_game_w / 34) / 2
            out_size = float(self.section_game_w / 34) / 100 * 50, float(self.section_game_w / 34) / 100 * 50

            # outbreak
            for o in range(0, self.outbreak + 1):
                self.game_canvas.create_rectangle(am_marker(out_a, out_size, (o, 0)),
                                                  fill="#ff9c00", outline='', tags="m1")
            # infection lvl
            pos = (8 if self.inflvl > 8 else self.inflvl)
            self.game_canvas.create_rectangle(am_marker(lvl_a, out_size, (pos, 0)),
                                              fill="#ff9c00", outline='', tags="m1")
            # supplies
            # max: 59
            # self.supplies
            sup_x = float(self.section_game_w) / 34 * 20
            sup_y = self.section_action + 8 + float(self.section_game_w / 34) / 2
            sup_s = float(self.section_game_w / 34) / 2 - 2
            self.game_canvas.create_rectangle(am_rect(sup_x, sup_y, sup_s, sup_s),
                                              fill="#4eff00", outline='', tags="m1")
            sup_h = (float(self.section_game_w) / 34) / 100 * 12
            sup_w = ((float(self.section_game_w) / 34) / 100 * 352) / 59 * self.supplies
            sup_t = (float(self.section_game_w) / 34) / 100 * 32
            self.game_canvas.create_rectangle(am_rect(sup_x + sup_s, sup_y + sup_t, sup_w, sup_h),
                                              fill="#4eff00", outline='', tags="m1")

            inf_a = float(self.section_game_w) / 34 * 12, self.section_action + 8
            inf_size = float(self.section_game_w / 34) / 100 * 25, float(self.section_game_w / 34) / 100 * 25
            # infection
            for i in range(0, 24):
                if 24 - self.infection[0] > i:
                    self.game_canvas.create_rectangle(am_marker(inf_a, inf_size, (i, 0)),
                                                      fill="#006bfd", outline='', tags="m1")
                if 24 - self.infection[1] > i:
                    self.game_canvas.create_rectangle(am_marker(inf_a, inf_size, (i, 1)),
                                                      fill="#fff300", outline='', tags="m1")
                if 24 - self.infection[2] > i:
                    self.game_canvas.create_rectangle(am_marker(inf_a, inf_size, (i, 2)),
                                                      fill="#189300", outline='', tags="m1")
                if 24 - self.infection[3] > i:
                    self.game_canvas.create_rectangle(am_marker(inf_a, inf_size, (i, 3)),
                                                      fill="#f10000", outline='', tags="m1")

            self.draw_overlay_bar()
            self.draw_marker(2)
            self.gameupdatelist['marker1'] = 0

        if marker == 2:
            self.game_canvas.delete("m2")

            heal_x = float(self.section_game_w) / 34 * 21
            heal_y = self.section_action + 8
            heal_w = (float(self.section_game_w) / 34) / 100 * 75
            for h in range(0, 4):
                if self.healing[h] == 1:
                    self.game_canvas.create_image(int(heal_x + heal_w * h), heal_y,
                                                  image=self.img_icon[0], anchor=NW, tags="m2")
                if self.healing[h] == 2:
                    self.game_canvas.create_image(int(heal_x + heal_w * h), heal_y,
                                                  image=self.img_icon[1], anchor=NW, tags="m2")
            self.gameupdatelist['marker2'] = 0

    def draw_overlay_bar(self):
        self.game_canvas.delete("status_overlay")
        # status overlay
        self.img_status = ImageTk.PhotoImage(
            self.img_status_raw.resize((int(self.section_game_w), int(self.section_game_w / 34)), Image.ANTIALIAS))
        self.game_canvas.create_image(0, self.section_action + 8, image=self.img_status, anchor=NW,
                                      tags="status_overlay")

    def draw_overlay_game(self):
        self.game_canvas.delete("game_overlay")
        # field overlay (city names)
        card_h = self.section_card - 8
        self.img_overlay_game = ImageTk.PhotoImage(
            self.img_overlay_game_raw.resize((int(self.section_game_w), int(self.section_game_w / 2.125)),
                                             Image.ANTIALIAS))
        self.game_canvas.create_image(0, card_h + 16, image=self.img_overlay_game, anchor=NW, tags="game_overlay")

    def draw_card_highlight(self, *args):
        self.game_canvas.delete("card_highlight")

        card_w = int((self.section_game_w - 72) / 8)
        card_h = int((self.section_game_w - 72) / 8 / 7 * 10)

        if len(args) > 0:
            if args[0] is None:
                self.game_canvas.delete("card_highlight_sel")
                self.game_canvas.delete("actioncard")
            else:
                if len(args) > 1:  # actioncard
                    tag = "actioncard"
                else:
                    tag = "card_highlight_sel"

                param = dict(fill="#000000", stipple=trans, activefill="", activestipple=trans, activewidth=3,
                             tags=tag)
                param['outline'] = args[1]
                param['activeoutline'] = args[1]
                for bg in args[0]:
                    self.game_canvas.create_rectangle(
                        am_rect(6 + (8 + card_w) * bg, 6, card_w + 4, card_h + 4), param)
                self.game_canvas.tag_bind(tag, "<ButtonRelease-1>", self.game_click)
                self.game_canvas.tag_bind("actioncard", "<Enter>", self.draw_tooltip_action)
                self.game_canvas.tag_bind("actioncard", "<Leave>", self.dismiss_tooltip)

        else:  # default
            self.game_canvas.delete("card_highlight_sel")
            if len(self.this_player_drawcards) > 0:
                if self.this_player_drawcards[0] == self.card_epidemie or self.game_STATE == "INFECT":
                    # Epidemie
                    self.game_canvas.create_rectangle(
                        am_rect(6 + (8 + card_w) * 7, 6, card_w + 4, card_h + 4),
                        outline="#00ff00", fill="#000000", stipple=trans,
                        activeoutline="#00ff00", activefill="", activestipple=trans, activewidth=3,
                        tags="card_highlight")
                else:
                    self.game_canvas.create_rectangle(
                        am_rect(6 + (8 + card_w) * 7, 6, card_w + 4, card_h + 4),
                        outline="#ff0000", fill="#000000", stipple=trans,
                        activeoutline="#ff0000", activefill="", activestipple=trans, activewidth=3,
                        tags="card_highlight")
                    if self.game_STATE == "SUPPLY" or self.game_STATE == "PASSIV":
                        for bg in range(0, 7):
                            if bg < len(self.this_player_cards):
                                self.game_canvas.create_rectangle(
                                    am_rect(6 + (8 + card_w) * bg, 6, card_w + 4, card_h + 4),
                                    outline="#ff0000", fill="#000000", stipple=trans,
                                    activeoutline="#ff0000", activefill="", activestipple=trans, activewidth=3,
                                    tags="card_highlight")
                            else:
                                self.game_canvas.create_rectangle(
                                    am_rect(6 + (8 + card_w) * bg, 6, card_w + 4, card_h + 4),
                                    outline="#00ff00", fill="#000000", stipple=trans,
                                    activeoutline="#00ff00", activefill="", activestipple=trans, activewidth=3,
                                    tags="card_highlight")

                self.game_canvas.tag_bind("card_highlight", "<Enter>", self.draw_tooltip)
                self.game_canvas.tag_bind("card_highlight", "<Leave>", self.dismiss_tooltip)
                self.game_canvas.tag_bind("card_highlight", "<ButtonRelease-1>", self.game_click)

    def draw_city_highlight(self, *args):
        self.game_canvas.delete("city_highlight")
        if len(args) > 0:
            for aw in args[0]:
                if aw < 48:
                    c = self.city[aw]
                    card_h = self.section_card - 8

                    # get anchor-position of city (center)
                    x = int(c.get('X') * float(int(self.section_game_w)) / 100)
                    y = int(c.get('Y') * float(int(self.section_game_w / 2.125) / 100) + (card_h + 16))
                    r = (self.section_game_w * 0.0125)

                    citytag = "CITY" + str(aw)

                    if len(args) > 1:  # action
                        param = dict(outline=args[1], fill="", width=2, activewidth=2, activefill=args[1])
                    else:
                        param = dict(outline="#00ff00", fill="", activefill="#ff0000")

                    param['tags'] = "city_highlight", citytag
                    self.game_canvas.create_oval(x - r, y - r, x + r, y + r, param)

                    self.game_canvas.tag_bind(citytag, "<ButtonRelease-1>",
                                              lambda event, t=citytag: self.game_click(event, t))

    def draw_tooltip(self, event):

        if event.y > self.section_field:  # BUTTONS
            posx = self.game_canvas.coords(tk.CURRENT)[0] + event.widget.winfo_width() / 68
            num = math.floor(float(posx) / self.section_game_w * 34)

            switcher = {
                3: "Forschungscenter errichten",
                4: "Krankheit behandeln",
                5: "Wissen teilen",
                6: "Heilmittel entdecken",
                7: "Aktionskarte spielen",
                8: "Krisenmanager",
                11: "Autofahrt/Schifffahrt",
                12: "Direktflug",
                13: "Charterflug",
                14: "Sonderflug",
                15: "Bewege anderen Spieler",
                16: "Bewege Spieler zu Spieler",
                32: "Zug beenden",
                33: "reload"
            }
            (switcher.get(num), "missing")

            self.game_canvas.itemconfigure(self.i_quicktip, fill="white", text=(switcher.get(num)))
            self.game_canvas.coords(self.i_quicktip, posx, self.section_field + 3)
        else:  # CARDS
            posx = self.game_canvas.coords(tk.CURRENT)[0] + event.widget.winfo_width() / 16
            num = math.floor(float(posx) / self.section_game_w * 8)

            if len(self.this_player_cards) <= num:
                text = "Karte aufnehmen"
            else:
                text = "Karte ersetzen"
            if num == 7:
                if self.this_player_drawcards[0] != self.card_epidemie:
                    if self.game_STATE == "SUPPLY":
                        text = "Karte verwerfen"
                    if self.game_STATE == "INFECT":
                        text = "Infizieren"
                    if self.game_STATE == "PASSIV":
                        text = "Karte nicht annehmen"
                else:
                    text = "Epidemie auslösen"

            self.game_canvas.itemconfigure(self.i_quicktip,
                                           fill="white",
                                           text=text,
                                           anchor=S)
            self.game_canvas.coords(self.i_quicktip, posx, self.section_card + 24)

    def draw_tooltip_action(self, event):

        posx = self.game_canvas.coords(tk.CURRENT)[0] + 8
        num = math.floor(float(posx) / self.section_game_w * 8)
        card = self.this_player_cards[num]

        switcher = {
            48: "Prognose\n\n"
                "Sieh die die obersten\n"
                "6 Karten des Nachzieh-\n"
                "stapels an und ordne\n"
                "sie neu.\n",
            49: "Freiflug\n\n"
                "Bewege eine beliebige\n"
                "Spielfigur in eine\n"
                "beliebige Stadt.\n",
            50: "Zähle Bevölkerung\n\n"
                "Wähle eine Karte aus dem\n"
                "Infektions-Ablagestapel\n"
                "und entferne sie aus dem\n"
                "Spiel.",
            51: "Staatliche Subvention\n\n"
                "Errichte ein Forschungs-\n"
                "zentrum ohne Karte in\n"
                "einer beliebigen Stadt.\n",
            52: "Eine ruhige Nacht\n\n"
                "Die nächste Infektions-\n"
                "phase wird komplett\n"
                "übersprungen.\n",
        }

        self.game_canvas.itemconfigure(self.i_actiontip,
                                       fill="white",
                                       text=switcher.get(card),
                                       anchor=NW)
        self.game_canvas.coords(self.i_actiontip, posx, self.section_card + 10)
        self.game_canvas.tag_raise(self.i_actiontip)
        r = self.game_canvas.create_rectangle(self.game_canvas.bbox(self.i_actiontip), stipple="gray50", fill="black", tags="abg")
        self.game_canvas.tag_lower(r, self.i_actiontip)

    def dismiss_tooltip(self, *event):
        self.game_canvas.delete("abg")
        self.game_canvas.itemconfigure(self.i_quicktip, fill="")
        self.game_canvas.itemconfigure(self.i_actiontip, fill="")
    # endregion


print("START")
app = Client()
app.mainloop()
app.running = False
print("wait for exit...")
