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

from Pandemie import libclient

########################################################################################################################
update_intervall = 3000
port = 9999
res_path = "D:/_PROJEKTE/2020/Python/Pandemie/"
php_path = "http://moja.de/public/python/getip.php"
# -------------------------------------------------------------------------------------------------------------------- #
trans = '@D:/_PROJEKTE/2020/Python/Pandemie/mat/transparent.xbm'
full = '@D:/_PROJEKTE/2020/Python/Pandemie/mat/full.xbm'
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


# region global functions ##############################################################################################
def inf_value(e):
    return e['value']


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


def create_request(raction, value):
    return dict(
        type="text/json",
        encoding="utf-8",
        content=dict(action=raction, value=value),
    )


class ResizingCanvas(Canvas):   # a subclass of Canvas for dealing with resizing of windows
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
    return x, y, x+w, y+h


def am_marker(xy, wh, pos):
    return xy[0] + wh[0] * pos[0], xy[1] + wh[1] * pos[1], \
           xy[0] + wh[0] * pos[0] + wh[0], xy[1] + wh[1] * pos[1] + wh[1]
# endregion


class Client(tk.Tk):

    def __init__(self):
        self._after = None
        self._update = False

        self.sel = selectors.DefaultSelector()
        self.updateintervall = update_intervall

        # region game variable #########################################################################################
        # player
        self.this_player_num = 0
        self.this_player_name = ''
        self.this_player_cards = []
        # self.this_player_draw_card = 54 TODO
        self.this_player_isrdy = 0
        self.this_player_turns = {'turns_left': 0, 'turn': 0, 'target': 0, 'use': 0, 'status': "otherplayer"}
        # region this player_turns - Aktionsphase: 4 Aktionen (turns) ##################################################
        #
        # turns_left: 0 - 5           0 = player not active
        #                               1-5 = remaining turns (max 4)
        #
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
        #    todo
        #    todo
        # endregion
        self.this_player_range = []
        self.all_player_name = ['-', '-', '-', '-']
        self.all_player_role = [0, 0, 0, 0]
        self.all_player_pos = [2, 2, 2, 2]  # start in Atlanta
        self.current_player = 0
        self.drawcard = []

        # gamestats
        self.outbreak = 0                   # 0-7
        self.inflvl = 0                     # 0-x
        self.supplies = 0                   # playercard-pile
        self.infection = [24, 24, 24, 24]   # 0-24
        self.healing = [0, 0, 0, 0]         # 0 = active,  1 = healed,  2 = exterminated

        # connection
        self.host = ''
        self.value = ''
        self.action = 'getVersion'
        self.localversion = 0
        self.game_status = "INIT"
        self.load = [0, 79, 0]  # [act load, total load, ready]
        self.ip_am = '127.0.0.1'
        self.ip_parts = self.ip_am.split(".")

        # Spielplan
        self.section_game_w = 1
        self.section_card = 0
        self.section_cardW = 0
        self.section_field = 0
        self.section_status = 0
        self.section_action = 0
        self.section_h100 = 0
        self.city = [{'ID':  0, 'posX':  5.2, 'posY': 24.4, 'farbe': 0, 'con': [ 1, 12, 39, 46],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'San Francisco'},
                     {'ID':  1, 'posX': 14.7, 'posY': 18.5, 'farbe': 0, 'con': [0, 12, 13,  2,  3],         'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Chicago'},
                     {'ID':  2, 'posX': 17.4, 'posY': 30.2, 'farbe': 0, 'con': [1,  5, 14],                 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 1, 'pincity': 0, 'name': 'Atlanta'},
                     {'ID':  3, 'posX': 22.1, 'posY': 18.0, 'farbe': 0, 'con': [1,  5,  4],                 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Montréal'},
                     {'ID':  4, 'posX': 27.8, 'posY': 19.9, 'farbe': 0, 'con': [3,  5,  6,  7],             'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'New York'},
                     {'ID':  5, 'posX': 25.3, 'posY': 29.4, 'farbe': 0, 'con': [ 4,  3,  2, 14],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Washington'},
                     {'ID':  6, 'posX': 40.6, 'posY': 25.9, 'farbe': 0, 'con': [ 4, 19, 24,  8,  7],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Madrid'},
                     {'ID':  7, 'posX': 41.6, 'posY': 10.3, 'farbe': 0, 'con': [ 4,  6,  8,  9],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'London'},
                     {'ID':  8, 'posX': 47.2, 'posY': 18.1, 'farbe': 0, 'con': [ 7,  6, 24, 10,  9],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Paris'},
                     {'ID':  9, 'posX': 49.1, 'posY':  7.2, 'farbe': 0, 'con': [ 7,  8, 10, 11],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Essen'},
                     {'ID': 10, 'posX': 52.2, 'posY': 15.1, 'farbe': 0, 'con': [ 9,  8, 26],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Mailand'},
                     {'ID': 11, 'posX': 57.3, 'posY':  4.3, 'farbe': 0, 'con': [ 9, 26, 27],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'St. Petersburg'},
                     {'ID': 12, 'posX':  6.8, 'posY': 40.1, 'farbe': 1, 'con': [47, 13,  1,  0],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Los Angeles'},
                     {'ID': 13, 'posX': 13.6, 'posY': 45.4, 'farbe': 1, 'con': [12, 16, 15, 14,  1],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Mexico Stadt'},
                     {'ID': 14, 'posX': 22.2, 'posY': 42.9, 'farbe': 1, 'con': [13, 15,  5,  2],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Miami'},
                     {'ID': 15, 'posX': 21.5, 'posY': 58.7, 'farbe': 1, 'con': [13, 16, 18, 19, 14],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Bogotá'},
                     {'ID': 16, 'posX': 18.9, 'posY': 75.7, 'farbe': 1, 'con': [13, 17, 15],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Lima'},
                     {'ID': 17, 'posX': 19.9, 'posY': 93.5, 'farbe': 1, 'con': [16],                        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Santiago'},
                     {'ID': 18, 'posX': 27.7, 'posY': 90.3, 'farbe': 1, 'con': [15, 19],                    'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Buenos Aires'},
                     {'ID': 19, 'posX': 32.0, 'posY': 78.2, 'farbe': 1, 'con': [15, 18, 20,  6],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Sao Paulo'},
                     {'ID': 20, 'posX': 46.5, 'posY': 55.8, 'farbe': 1, 'con': [19, 21, 23],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Lagos'},
                     {'ID': 21, 'posX': 51.0, 'posY': 66.3, 'farbe': 1, 'con': [20, 22, 23],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Kinshasa'},
                     {'ID': 22, 'posX': 55.4, 'posY': 82.6, 'farbe': 1, 'con': [21, 23],                    'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Johannisburg'},
                     {'ID': 23, 'posX': 56.0, 'posY': 53.0, 'farbe': 1, 'con': [20, 21, 22, 25],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Khartum'},
                     {'ID': 24, 'posX': 48.7, 'posY': 34.6, 'farbe': 2, 'con': [ 6, 25, 26,  8],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Algier'},
                     {'ID': 25, 'posX': 54.4, 'posY': 37.5, 'farbe': 2, 'con': [24, 23, 29, 28, 26],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Kairo'},
                     {'ID': 26, 'posX': 55.5, 'posY': 24.3, 'farbe': 2, 'con': [24, 25, 28, 27, 11, 10],    'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Istanbul'},
                     {'ID': 27, 'posX': 61.3, 'posY': 15.0, 'farbe': 2, 'con': [11, 26, 30],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Moskau'},
                     {'ID': 28, 'posX': 60.7, 'posY': 32.3, 'farbe': 2, 'con': [26, 25, 29, 31, 30],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Bagdad'},
                     {'ID': 29, 'posX': 61.6, 'posY': 46.8, 'farbe': 2, 'con': [25, 31, 28],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Riad'},
                     {'ID': 30, 'posX': 66.3, 'posY': 22.5, 'farbe': 2, 'con': [27, 28, 31, 33],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Teheran'},
                     {'ID': 31, 'posX': 67.9, 'posY': 37.9, 'farbe': 2, 'con': [28, 29, 32, 33, 30],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Karatschi'},
                     {'ID': 32, 'posX': 68.5, 'posY': 49.3, 'farbe': 2, 'con': [31, 34, 33],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Mumbai'},
                     {'ID': 33, 'posX': 73.3, 'posY': 33.1, 'farbe': 2, 'con': [30, 31, 32, 34, 35],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Delhi'},
                     {'ID': 34, 'posX': 74.3, 'posY': 57.5, 'farbe': 2, 'con': [32, 44, 40, 35, 33],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Chennai'},
                     {'ID': 35, 'posX': 78.5, 'posY': 36.9, 'farbe': 2, 'con': [33, 34, 40, 41],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Kalkutta'},
                     {'ID': 36, 'posX': 82.6, 'posY': 18.6, 'farbe': 3, 'con': [37, 38],                    'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Peking'},
                     {'ID': 37, 'posX': 89.3, 'posY': 18.0, 'farbe': 3, 'con': [36, 38, 39],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Seoul'},
                     {'ID': 38, 'posX': 83.2, 'posY': 29.9, 'farbe': 3, 'con': [36, 41, 42, 39, 37],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Shanghai'},
                     {'ID': 39, 'posX': 94.5, 'posY': 24.3, 'farbe': 3, 'con': [37, 38, 43,  0],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Tokyo'},
                     {'ID': 40, 'posX': 79.6, 'posY': 50.3, 'farbe': 3, 'con': [34, 44, 45, 41, 35],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Bangkok'},
                     {'ID': 41, 'posX': 83.9, 'posY': 43.1, 'farbe': 3, 'con': [35, 40, 45, 46, 42, 38],    'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Hong Kong'},
                     {'ID': 42, 'posX': 89.8, 'posY': 41.0, 'farbe': 3, 'con': [41, 46, 43, 38],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Taipeh'},
                     {'ID': 43, 'posX': 95.1, 'posY': 36.1, 'farbe': 3, 'con': [39, 42],                    'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Osaka'},
                     {'ID': 44, 'posX': 79.5, 'posY': 71.1, 'farbe': 3, 'con': [34, 47, 45, 40],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Jakarta'},
                     {'ID': 45, 'posX': 84.2, 'posY': 61.4, 'farbe': 3, 'con': [44, 46, 41, 40],            'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Ho-Chi-MinH-Stadt'},
                     {'ID': 46, 'posX': 91.4, 'posY': 60.6, 'farbe': 3, 'con': [45, 47,  0, 42, 41],        'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Manila'},
                     {'ID': 47, 'posX': 95.6, 'posY': 93.1, 'farbe': 3, 'con': [46, 44, 12],                'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pincity': 0, 'name': 'Sydney'}]
        # endregion

        tk.Tk.__init__(self)

        # region resources -> define resources here    ----------------------------------------------------------------#
        #                     load images in thread task
        #                     load_res_async(self): as it takes a while, display loading-bar
        self.img_map_raw = Image        # map (BG)
        self.img_map = ImageTk
        self.img_map_name_raw = Image   # map overlay (FG)
        self.img_map_name = ImageTk
        self.img_status_raw = Image     # statusbar overlay
        self.img_status = ImageTk
        self.img_action_raw = Image     # actionbar overlay
        self.img_action = ImageTk
        self.img_char = []              # character cards
        self.img_c1_raw = []            # player cards [01..54]
        self.img_c1 = []
        self.img_inf_raw = []           # infection marker: inf_0_1.png
        self.img_inf = []
        self.img_center_raw = Image     # center
        self.img_center = ImageTk
        self.img_p_raw = []             # player_piece
        self.img_p = []

        # test
        self.img_trans_raw = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        self.img_trans = ImageTk.PhotoImage(self.img_trans_raw)
        self.img_border_raw = Image
        self.img_border = ImageTk
        # endregion

        # region window 00 connection load
        self.LOADframe = Frame(self)
        self.load_canvas = ResizingCanvas(self.LOADframe, width=512, height=140, highlightthickness=0)
        self.loading_bar = self.load_canvas.create_rectangle(am_rect(8, 72, 0, 5), fill="#09f", outline="")
        self.load_canvas.create_text(8, 70, text='connect to server...', anchor='sw', tags="loadingtext")
        # endregion

        # region window 01 connection connect
        self.title("Pandemie | Verbindung")
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
        self.btn_participate = Button(self.PREPframe, text='Teilnehmen', command=self.btn_player_enter)
        self.btn_start = Button(self.PREPframe, text='Spiel starten', command=self.btn_player_rdy, state=DISABLED)
        self.lbl2 = Label(self.PREPframe, text="Deine Rolle:", font="Helvetica 12 bold")

        self.player_frame = Frame(self.PREPframe)
        self.lbl_head_player = Label(self.player_frame, text="Spieler", font="Helvetica 12 bold")
        self.lbl_head_role = Label(self.player_frame, text="Rolle", font="Helvetica 12 bold")

        self.lbl_player_name = []
        self.lbl_player_func = []
        for p in range(0, 4):
            self.lbl_player_name.append(Label(self.player_frame, text="Spieler " + str(p), font="Helvetica 12"))
            self.lbl_player_func.append(Label(self.player_frame, text="-", font="Helvetica 12"))

        self.role_image = Label(self.PREPframe)

        self.recon_frame = Frame(self)
        self.recon_label = Label(self.recon_frame, text="Player No.: ", font="Helvetica 24 bold")
        self.entry_re = Entry(self.recon_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.btn_startrecon = Button(self.recon_frame, text='START', justify="center", command=self.btn_recon_cmd)
        self.recon_stat = Label(self, text="")
        # endregion

        # region window game UI
        self.game_frame = Frame(self)
        self.old_window_w = 0
        self.old_window_h = 0
        self.game_canvas = ResizingCanvas(self.game_frame, width=1, height=1, bg="#333", highlightthickness=0)

        self.i_quicktip = self.game_canvas.create_text(0, 0)
        self.i_action = Label(self.game_canvas)
        self.i_status = Label(self.game_canvas)
        self.txt_action = ""
        self.txt_status = ""
        # endregion

        print("window_00_load")
        self.window_00_load()

    # region functions #################################################################################################
    def start_connection(self, shost, sport, request):
        addr = (shost, sport)
        # print("starting connection to", addr)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        message = libclient.Message(self.sel, sock, addr, request)
        self.sel.register(sock, events, data=message)

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

        aktpos = self.all_player_pos[self.this_player_num]

        # get distance to specific city
        if len(args) > 0:
            target = args[0]
            path = [target]
            while get_pre(aktpos, target) != self.all_player_pos[self.this_player_num]:
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
    # endregion

    # region Windows and UI ############################################################################################
    def clear_after(self):
        if self._after is not None:
            self.after_cancel(self._after)
            self._after = None

    def set_after(self, func, *args):

        time_short = args[0] if len(args) > 0 else 50
        time_long = args[0] if len(args) > 0 else update_intervall

        self.clear_after()
        if self._update:
            self._after = self.after(time_short, func)
        else:
            self._after = self.after(time_long, func)

    def window_00_load(self):
        self.clear_after()

        if self.load[0] == 0:   # INIT
            self.LOADframe.pack()
            self.load_canvas.pack()

            self.load[0] += 1  # end init
            thread1 = threading.Thread(target=self.load_res_async)
            thread1.start()

        if self.load[2] == 1:   # switch text after connectiondata is loaded
            self.load_canvas.delete("loadingtext")
            self.load_canvas.create_text(8, 70, text='loading resources...', anchor='sw', tags="loadingtext")
            self.load[2] = 2

        if self.load[2] == 2:   # load rescources and display bar
            x0, y0, x1, y1 = self.load_canvas.coords(self.loading_bar)
            self.load_canvas.coords(self.loading_bar, x0, y0, (512-21) * self.load[0] / self.load[1] + 5, y1)

        if self.load[2] == 3:                           # leave loop and start connection window
            self.set_after(self.window_01_connect, 500)
        else:                                         # loop self
            self.set_after(self.window_00_load, 1)

    def load_res_async(self):
        print(" async load: start")
        # connection
        # try to get ip for server from php-script
        self.ip_am = urllib.request.urlopen(php_path).read().decode('utf8').strip()
        self.ip_parts = self.ip_am.split(".")

        self.load[2] = 1

        #                     [0] increment
        self.load[1] = 80   # [1] total number of elements to load
        #                     [2] boolean to 1 when ready

        self.img_map_raw = Image.open(res_path + "mat/world.png")
        self.img_map = ImageTk.PhotoImage(self.img_map_raw)
        self.load[0] += 1   # 1

        self.img_map_name_raw = Image.open(res_path + "mat/namen.png")
        self.img_map_name = ImageTk.PhotoImage(self.img_map_name_raw)
        self.load[0] += 1   # 2

        self.img_action_raw = Image.open(res_path + "mat/actionbar.png")
        self.img_action = ImageTk.PhotoImage(self.img_action_raw)
        self.load[0] += 1   # 3

        self.img_status_raw = Image.open(res_path + "mat/statusbar.png")
        self.img_status = ImageTk.PhotoImage(self.img_status_raw)
        self.load[0] += 1   # 4

        self.img_center_raw = Image.open(res_path + "mat/center.png")
        self.img_center = ImageTk.PhotoImage(self.img_center_raw)
        self.load[0] += 1   # 5

        for c in range(1, 56):
            # print(str(c))
            self.img_c1_raw.append(Image.open(res_path + "cards/c1_" + "{:02d}".format(c) + ".png"))
            self.img_c1.append(ImageTk.PhotoImage(self.img_c1_raw[c-1]))
            self.load[0] += 1   # 6-59

        for c in range(0, 8):
            self.img_char.append(ImageTk.PhotoImage(
                Image.open(res_path + "cards/char_" + str(c) + ".png").resize((350, 500), Image.ANTIALIAS)))
            self.load[0] += 1   # 60-66

        self.role_image = Label(self.PREPframe, image=self.img_char[0])

        self.load[0] += 1   # 67

        self.img_inf_raw = [[Image.open(res_path + "mat/inf_" + str(x) + "_" + str(y + 1) + ".png") for x in range(4)]
                            for y in range(4)]

        self.load[0] += 2   # 69

        self.img_inf = [[[ImageTk.PhotoImage(self.img_inf_raw[x][y]) for x in range(4)] for y in range(4)] for z in
                        range(3)]

        self.load[0] += 2   # 71

        for p in range(0, 7):
            self.img_p_raw.append(Image.open(res_path + "mat/player_" + str(p + 1) + ".png"))
            self.img_p.append(ImageTk.PhotoImage(self.img_p_raw[p]))
            self.load[0] += 1   # 72-79

        self.img_border_raw = Image.open(res_path + "mat/border_square.png")
        self.img_border = ImageTk.PhotoImage(self.img_border_raw)
        self.load[0] += 1  # 1

        # loading done
        print(" async load: done")
        self.load[2] = 3

    def window_01_connect(self):
        self.clear_after()
        print("window_01_connect")
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
        self.btn_con.bind('<Return>', self.window_02b_recon)    # TODO DELETE THIS LINE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #self.btn_con.bind('<Return>', self.window_02a_game_prep) TODO UNCOMMENT THIS LINE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def window_02a_game_prep(self, event=None):
        print("window_02a_game_prep")
        # global client_host
        self.host = self.entry1.get() + '.' + self.entry2.get() + '.' + self.entry3.get() + '.' + self.entry4.get()
        print(self.host)

        self.CONframe.destroy()

        self.title("Spielvorbereitung")
        self.geometry("700x600")
        self.PREPframe.grid()
        self.lbl1.grid(row=0, column=1, padx=5, pady=18, sticky=E)
        self.entry_n.grid(row=0, column=2, padx=5, pady=18, sticky=W + E)
        self.btn_participate.grid(row=0, column=3, padx=5, pady=18, sticky=W)
        self.btn_start.grid(row=0, column=4, padx=5, pady=18, sticky=W)
        self.lbl2.grid(row=1, column=1, padx=5, pady=0, sticky=W + S, columnspan=2)
        self.role_image.grid(row=2, column=1, padx=5, pady=5, columnspan=2)

        self.player_frame.grid(row=1, column=3, padx=5, pady=5, sticky=N, rowspan=2, columnspan=2)
        self.lbl_head_player.grid(row=1, column=3, padx=5, pady=0, sticky=E)
        self.lbl_head_role.grid(row=1, column=4, padx=5, pady=0, sticky=W)

        for p in range(0, 4):
            self.lbl_player_name[p].grid(row=2+p, column=3, padx=5, pady=5, sticky=E)
            self.lbl_player_func[p].grid(row=2+p, column=4, padx=5, pady=5, sticky=E)

        self.task()

    def window_02b_recon(self, event=None):
        # global client_host
        self.host = self.entry1.get() + '.' + self.entry2.get() + '.' + self.entry3.get() + '.' + self.entry4.get()
        print("reconnect", self.host)

        self.CONframe.destroy()

        self.title("Reconnect")

        self.entry_re.insert(0, "0")  # TODO DELETE THIS LINE ##########################################################
        self.this_player_turns['turns_left'] = 4    # TODO DELETE THIS LINE ############################################

        self.recon_frame.pack(side=TOP, pady=(40, 0))
        self.recon_label.pack(side="left")
        self.entry_re.pack(side="left")
        self.btn_startrecon.pack(side="right", padx=(10, 0), pady=5)
        self.recon_stat.pack(side="bottom")

        self.btn_startrecon.focus_set()
        self.btn_startrecon.bind('<Return>', self.btn_recon_cmd)
    # endregion

    def display_game(self, updatedata):

        # region get actual window dimension and calculate aspect-ration
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
        self.section_cardW = card_w + 8
        self.section_field = int(self.section_game_w / 2.125) + self.section_card + 8
        self.section_action = self.section_field + int(self.section_game_w / 34) + 8
        self.section_status = self.section_action + int(self.section_game_w / 34) + 8
        # endregion

        self.outbreak = 5  # TODO DELETE THIS LINE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.inflvl = 3    # TODO DELETE THIS LINE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        if self.current_player == self.this_player_num:
            if self.this_player_turns["turns_left"] > 1:
                self.txt_status = "Aktionsphase: " + str(
                    self.this_player_turns["turns_left"]) + " Aktionen verbleibend."
            elif self.this_player_turns["turns_left"] == 1:
                self.txt_status = "Aktionsphase: Eine Aktion verbleibend."
        else:
            self.txt_status = self.all_player_name[self.current_player] + " ist am Zug."

        if self.old_window_h != win_h or self.old_window_w != win_w:  # resize #########################################
            print("RESIZE")
            for child in self.winfo_children():     # destroy all
                child.destroy()

            # set base frame over whole window
            self.game_frame = Frame(self, width=win_w, height=win_h, bg="#333")
            # self.game_frame.pack(fill=BOTH, expand=YES)
            self.game_frame.place(relx=0.5, rely=0.5, width=win_w, height=win_h, anchor=CENTER)

            # canvas
            self.game_canvas = ResizingCanvas(self.game_frame, width=self.section_game_w, height=game_h,
                                              bg="#333", highlightthickness=0)
            self.game_canvas.bind("<Button-1>", self.callback)
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

            # DRAW -----------------------------------------------------------------------------------------------------
            self.draw_cards()

            for c in range(0, 48):  # loop through citys
                self.draw_cities(c)
            self.draw_overlay_game()
            self.draw_player()

            self.draw_marker(1)
            # TODO status bar marker 2
            # todo healing 1-4
            self.draw_overlay_status()

            self.draw_action()

            # TODO BTN
            btnx = (float(self.section_game_w) / 34)
            btny = self.section_field + 8
            btns = int((float(self.section_game_w) / 34))

            self.img_trans = ImageTk.PhotoImage(self.img_trans_raw.resize((btns, btns), Image.ANTIALIAS))
            self.img_border = ImageTk.PhotoImage(self.img_border_raw.resize((btns, btns), Image.ANTIALIAS))

            self.game_canvas.create_image(3 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(4 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(5 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(6 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(7 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(10 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(11 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(12 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(13 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(14 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')
            self.game_canvas.create_image(15 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')

            self.game_canvas.create_image(17 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')

            self.game_canvas.create_image(33 * btnx, btny, image=self.img_trans, anchor=NW, tags='btnarea')

            self.i_quicktip = self.game_canvas.create_text(0, 0, text="", fill="", anchor=S,
                                                           font=('Helvetica', 10), tags="info")

            self.game_canvas.tag_bind("btnarea", "<ButtonRelease-1>", self.btn_action_selector)
            self.game_canvas.tag_bind("btnarea", "<Enter>", self.tooltip_show)
            self.game_canvas.tag_bind("btnarea", "<Leave>", self.tooltip_dismiss)

            # set variables for resize-check
            self.old_window_w = win_w
            self.old_window_h = win_h

            # self.game_canvas.addtag_all("all")
        else:  # only update, no resize

            if "cards" in updatedata:
                print("update player cards")
                self.draw_cards()
            if "city" in updatedata:
                for c in updatedata['city']:
                    print("update city", str(c))
                    self.draw_cities(c)
                if len(updatedata['city']) > 0:
                    self.draw_overlay_game()
                    self.draw_player()

                if "playerpos" in updatedata and len(updatedata['city']) == 0:
                    print("update player pos")
                    self.draw_player()

            if "marker1" in updatedata:
                print("update outbreak, inflvl, supplies")
                self.draw_marker(1)

            if "marker2" in updatedata:
                print("update inf0-4, healing")

            if "marker1" in updatedata or "marker2" in updatedata:
                self.draw_overlay_status()

        self.set_after(self.task)


    # region draw elements #############################################################################################

    def draw_cards(self):
        self.game_canvas.delete("cards")
        card_w = int((self.section_game_w - 72) / 8)
        card_h = int((self.section_game_w - 72) / 8 / 7 * 10)
        place = 0
        for card in self.this_player_cards:
            self.img_c1[card] = ImageTk.PhotoImage(
                self.img_c1_raw[card].resize((int(card_w), int(card_h)), Image.ANTIALIAS))
            self.game_canvas.create_image(
                8 + (8 + card_w) * place, 8, image=self.img_c1[card], anchor=NW, tags="cards")
            place += 1
        # draw card pile (back)
        if len(self.drawcard) > 0:
            self.img_c1[self.drawcard[0]] = ImageTk.PhotoImage(
                self.img_c1_raw[self.drawcard[0]].resize((int(card_w), int(card_h)), Image.ANTIALIAS))
            self.game_canvas.create_image(
                8 + (8 + card_w) * 7, 8, image=self.img_c1[self.drawcard[0]], anchor=NW, tags="cards")
        else:
            self.draw_card_highlight(0)
            self.img_c1[54] = ImageTk.PhotoImage(
                self.img_c1_raw[54].resize((int(card_w), int(card_h)), Image.ANTIALIAS))
            self.game_canvas.create_image(
                8 + (8 + card_w) * 7, 8, image=self.img_c1[54], anchor=NW, tags="cards")

    def draw_cities(self, aw):
        c = self.city[aw]
        self.game_canvas.delete("c" + str(c.get('ID')))
        card_h = self.section_card - 8
        s_inf = 320 * self.section_game_w / (3380 * 2)  # variable for marker size (half the size)
        s_cen = s_inf * 120 / 320

        # temporary infection item for current city
        infection = [{'i': 0, 'value': 0}, {'i': 1, 'value': 0}, {'i': 2, 'value': 0}, {'i': 3, 'value': 0}]
        for i in range(0, 4):
            infection[i]['value'] = c.get('i' + str(i))

        # sort infection (highest value first -> highest infection will be drawn on most inner ring
        infection.sort(key=inf_value, reverse=True)

        # get anchor-position of city (center)
        x = int(c.get('posX') * float(int(self.section_game_w)) / 100)
        y = int(c.get('posY') * float(int(self.section_game_w / 2.125) / 100) + (card_h + 16))

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

        if c.get('center') == 1:
            x = int(c.get('posX') * float(int(self.section_game_w)) / 100) - int(s_cen / 120 * 82)
            y = int(c.get('posY') * float(int(self.section_game_w / 2.125) / 100) + (card_h + 16)) + int(
                s_cen / 120 * 50)
            self.game_canvas.create_image(x, y,
                                          image=self.img_center,
                                          anchor=CENTER,
                                          tags=("c" + str(c.get('ID')), "center"))

    def draw_city_highlight(self, myrange):
        self.game_canvas.delete("city_highlight")
        for aw in myrange:
            if aw < 48:
                c = self.city[aw]
                card_h = self.section_card - 8
                s_inf = 320 * self.section_game_w / (3380 * 2)  # variable for marker size (half the size)
                s_cen = s_inf * 120 / 320

                # get anchor-position of city (center)
                x = int(c.get('posX') * float(int(self.section_game_w)) / 100)
                y = int(c.get('posY') * float(int(self.section_game_w / 2.125) / 100) + (card_h + 16))
                r = (self.section_game_w * 0.0125)
                self.game_canvas.create_oval(x-r, y-r, x+r, y+r, outline="#00ff00", fill="", activefill="#ff0000", tags="city_highlight")

    def draw_card_highlight(self, *args):
        self.game_canvas.delete("card_highlight")

        if len(args) == 0:
            card_w = int((self.section_game_w - 72) / 8)
            card_h = int((self.section_game_w - 72) / 8 / 7 * 10)

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
            if len(self.drawcard) > 0:
                self.game_canvas.create_rectangle(
                    am_rect(6 + (8 + card_w) * 7, 6, card_w + 4, card_h + 4),
                    outline="#ff0000", fill="#000000", stipple=trans,
                    activeoutline="#ff0000", activefill="", activestipple=trans, activewidth=3,
                    tags="card_highlight")

    def draw_overlay_game(self):
        self.game_canvas.delete("game_overlay")
        # field overlay (city names)
        card_h = self.section_card - 8
        self.img_map_name = ImageTk.PhotoImage(
            self.img_map_name_raw.resize((int(self.section_game_w), int(self.section_game_w / 2.125)), Image.ANTIALIAS))
        self.game_canvas.create_image(0, card_h + 16, image=self.img_map_name, anchor=NW, tags="game_overlay")

    def draw_overlay_status(self):
        self.game_canvas.delete("status_overlay")
        # status overlay
        self.img_status = ImageTk.PhotoImage(
            self.img_status_raw.resize((int(self.section_game_w), int(self.section_game_w / 34)), Image.ANTIALIAS))
        self.game_canvas.create_image(0, self.section_action + 8, image=self.img_status, anchor=NW,
                                      tags="status_overlay")

    def draw_player(self):
        self.game_canvas.delete("player")
        # player 80x175
        s_inf = 320 * self.section_game_w / (3380 * 2)  # variable for marker size (half the size)
        s_cen = s_inf * 120 / 320
        h_ply = s_cen * 175 / 120
        w_ply = s_cen * 80 / 120
        for c in self.city:
            c['pincity'] = 0  # reset player
            for p in range(0, 4):
                if self.all_player_pos[p] == c.get('ID') and self.all_player_role[p] != 0:
                    c['pincity'] += 1
                    self.img_p[self.all_player_role[p] - 1] = ImageTk.PhotoImage(
                        self.img_p_raw[self.all_player_role[p] - 1]
                            .resize((int(w_ply), int(h_ply)), Image.ANTIALIAS))
                    x = int(c.get('posX') * float(int(self.section_game_w)) / 100) \
                        - int(s_cen / 120 * 39) \
                        + int(s_cen / 120 * 52) * c.get('pincity')
                    y = int(c.get('posY') * float(int(self.section_game_w / 2.125) / 100) + (self.section_card + 8)) \
                        - int(s_cen / 120 * 41)
                    self.game_canvas.create_image(
                        x, y, image=self.img_p[self.all_player_role[p] - 1], anchor=CENTER, tags="player")

    def draw_marker(self, marker):
        # Marker:
        #   Ausbruchsmarker: 0-7 -> 8 = Verloren-> 4
        #   Infektionsleiste:   2,2,2,3,3,4,4   -> 4
        #   Heilmittel                          -> 4
        # verbleibende seuchenwürfel 24 * 1/4   -> 6
        # verbleibende Spielerkarten = versorgung/supplies
        if marker == 1:
            # marker 1
            out_a = float(self.section_game_w) / 34 * 5, self.section_action + 9
            lvl_a = float(self.section_game_w) / 34 * 5, self.section_action + 8 + float(self.section_game_w / 34) / 100 * 56
            inf_a = float(self.section_game_w) / 34 * 12, self.section_action + 8
            out_size = float(self.section_game_w / 34) / 100 * 50, float(self.section_game_w / 34) / 100 * 50
            inf_size = float(self.section_game_w / 34) / 100 * 25, float(self.section_game_w / 34) / 100 * 25

            # outbreak
            for o in range(0, self.outbreak):
                self.game_canvas.create_rectangle(am_marker(out_a, out_size, (o, 0)),
                                                  fill="#ff00ff", outline='', tags="m1")
            # infection lvl
            pos = (8 if self.inflvl > 8 else self.inflvl)
            self.game_canvas.create_rectangle(am_marker(lvl_a, out_size, (pos, 0)),
                                              fill="#ff00ff", outline='', tags="m1")
            # supplies
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
        if marker == 2:
            # marker 2
            # TODO marker 2
            print("")

    def draw_action(self):
        self.img_action = ImageTk.PhotoImage(
            self.img_action_raw.resize((int(self.section_game_w), int(self.section_game_w / 34)), Image.ANTIALIAS))
        self.game_canvas.create_rectangle(
            am_rect(0, self.section_field + 8, self.section_game_w, int(self.section_game_w / 34)),
            fill="#282828", outline='#3a3a3a')
        self.game_canvas.create_image(0, self.section_field + 8, image=self.img_action, anchor=NW, tags="action")

    def tooltip_show(self, event):

        event.widget.itemconfigure(tk.CURRENT, image=self.img_border)

        posx = self.game_canvas.coords(tk.CURRENT)[0] + event.widget.winfo_width() / 68
        num = math.floor(float(posx) / self.section_game_w * 34)

        switcher = {
             3: "Forschungscenter errichten",
             4: "Krankheit behandeln",
             5: "Wissen teilen",
             6: "Heilmittel entdecken",
             7: "special",
            10: "Autofahrt/Schifffahrt",
            11: "Direktflug",
            12: "Charterflug",
            13: "Sonderflug",
            14: "c1",
            15: "c2",
            17: "execute",
            33: "reload"
        }
        (switcher.get(num), "missing")

        self.game_canvas.itemconfigure(self.i_quicktip, fill="white", text=(switcher.get(num)))
        self.game_canvas.coords(self.i_quicktip, posx, self.section_field + 3)

    def tooltip_dismiss(self, event):
        event.widget.itemconfigure(tk.CURRENT, image=self.img_trans)
        self.game_canvas.itemconfigure(self.i_quicktip, fill="")
    # endregion

    # region UI elements ###############################################################################################
    def btn_action_selector(self, event):
        posx = self.game_canvas.coords(tk.CURRENT)[0] + event.widget.winfo_width() / 68
        num = math.floor(float(posx) / self.section_game_w * 34)

        # self.this_player_turns['turns_left'] = 4  # TODO DELETE THIS LINE ##########################################

        print("action-BTN", str(num), "clicked.")
        # assign BTN number to action ##################################################################################
        switcher = {
            10: self.btn_10_turn_move,
            11: self.btn_11_turn_fly_direct,
            12: self.btn_12_turn_fly_charter,
            13: self.btn_13_turn_fly_special,
            17: self.btn_17_turn_execute,
            33: self.btn_33_game_reload
        }
        func = switcher.get(num, lambda: None)

        if self.this_player_turns['turns_left'] > 0:
            func()  # execute
        else:
            self.txt_action = "keine Züge vorhanden"

        self.i_action.configure(text=self.txt_action)  # update description for player
        self.i_status.configure(text=self.txt_status)  # update description for player

    def btn_player_enter(self):
        playername = self.entry_n.get()
        if playername != "":
            self.entry_n.configure(state=DISABLED)
            self.btn_participate.configure(state=DISABLED)
            self.action = "setPlayer"
            self.this_player_name = playername.strip()
            self.value = playername.strip()

    def btn_player_rdy(self):
        self.btn_start.configure(bg="SeaGreen1", text="Warte auf andere Spieler", state=DISABLED)
        self.this_player_isrdy = 1
        self.action = 'player_rdy'
        self.value = self.this_player_num

    def btn_recon_cmd(self, event=None):
        print("BTN_recon")
        try:
            num = int(self.entry_re.get())
            if 0 <= num < 4:
                print("recon", str(num))
                self.this_player_num = num

                self.action = 'recon'
                self.value = num
                self.recon_frame.destroy()
                self.task()

            else:
                self.recon_stat.config(text="invalid player, enter 'Player No.' from 0 to 3")
        except ValueError:
            self.recon_stat.config(text="invalid entry, enter numeric value from 0 to 3")
            print("Exeption")

    def btn_10_turn_move(self):
        self.this_player_turns['turn'] = 10
        self.get_player_path()
        self.draw_city_highlight(self.this_player_range)
        self.txt_action = "Bewegen: Wähle Ziel. (keine Karte notwendig)"

    def btn_11_turn_fly_direct(self):
        self.this_player_turns['turn'] = 11
        self.draw_city_highlight(self.this_player_cards)
        self.txt_action = "Direktflug: Wähle Ziel. (eine Karte wird benötigt)"

    def btn_12_turn_fly_charter(self):
        if self.all_player_pos[self.this_player_num] in self.this_player_cards:
            self.this_player_turns['turn'] = 12
            self.txt_action = "Charterflug: Wähle Zielstadt."
            allcitys = [x for x in range(48)]
            allcitys.remove(self.all_player_pos[self.this_player_num])
            self.draw_city_highlight(allcitys)
        else:
            self.txt_action = "Charterflug nicht möglich. (Karte vom Standort wird benötigt)"

    def btn_13_turn_fly_special(self):
        if self.city[self.all_player_pos[self.this_player_num]]['center']:
            self.this_player_turns['turn'] = 13
            self.txt_action = "Sonderflug: Wähle Zielstadt mit Forschungscenter."
            citys = []
            for c in self.city:
                if c['center']:
                    citys.append(c['ID'])
            citys.remove(self.all_player_pos[self.this_player_num])
            self.draw_city_highlight(citys)
        else:
            self.txt_action = "Sonderflug nicht möglich. (Forschungszentrum benötigt)"

    def btn_17_turn_execute(self):

        # region check requirements and generate request ###############################################################
        def check_10():
            if self.this_player_turns['target'] != self.all_player_pos[self.this_player_num] and \
                    self.this_player_turns['use'] <= self.this_player_turns['turns_left']:

                # server request
                self.value = {'player':     self.this_player_num,
                              'moveto':     self.this_player_turns['target'],
                              'usedcards':  []}
                self.action = 'player_move'
                # update game
                self.draw_city_highlight([])
                self.this_player_turns['turns_left'] -= self.this_player_turns['use']
                return ""
            else:
                self.draw_city_highlight([])
                return "Zug ungültig"

        def check_11():
            if self.this_player_turns['use'] <= self.this_player_turns['turns_left']:
                # server request
                self.value = {'player': self.this_player_num,
                              'moveto': self.this_player_turns['target'],
                              'usedcards': [self.this_player_turns['target']]}
                self.action = 'player_move'
                # update game
                self.draw_city_highlight([])
                self.this_player_turns['turns_left'] -= self.this_player_turns['use']
                return ""
            else:
                self.draw_city_highlight([])
                return "Zug ungültig"

        def check_12():
            if self.all_player_pos[self.this_player_num] in self.this_player_cards and \
                    self.this_player_turns['use'] <= self.this_player_turns['turns_left']:
                # server request
                self.value = {'player': self.this_player_num,
                              'moveto': self.this_player_turns['target'],
                              'usedcards': [self.all_player_pos[self.this_player_num]]}
                self.action = 'player_move'
                self.draw_city_highlight([])
                self.this_player_turns['turns_left'] -= self.this_player_turns['use']
            else:
                self.draw_city_highlight([])
                return "Zug ungültig"

        def check_13():
            if self.this_player_turns['turn'] == 13 and \
                    self.this_player_turns['use'] <= self.this_player_turns['turns_left'] and \
                    self.city[self.all_player_pos[self.this_player_num]]['center']:
                # server request
                self.value = {'player': self.this_player_num,
                              'moveto': self.this_player_turns['target'],
                              'usedcards': []}
                self.action = 'player_move'
                self.draw_city_highlight([])
                self.this_player_turns['turns_left'] -= self.this_player_turns['use']
            else:
                self.draw_city_highlight([])
                return "Zug ungültig"
        # endregion

        print("TURN EXECUTE")
        switcher = {
            10: check_10,
            11: check_11,
            12: check_12,
            13: check_13,
            # 31: self.btn_17_turn_execute,
            33: self.btn_33_game_reload
        }
        func = switcher.get(self.this_player_turns['turn'], lambda: "Zug ungültig")
        if self.this_player_turns['turns_left'] > 0:
            self.txt_action = func()  # execute

            if self.this_player_turns["turns_left"] > 1:
                self.txt_status = "Aktionsphase: " + str(
                    self.this_player_turns["turns_left"]) + " Aktionen verbleibend."
            elif self.this_player_turns["turns_left"] == 1:
                self.txt_status = "Aktionsphase: Eine Aktion verbleibend."
            else:  # turn is over -> after-turn-phase
                self.txt_action = ""
                self.txt_status = "Nachschubpahse"
                # self.this_player_turns["status"] = "supply_1"
                self.value = self.this_player_num
                self.action = 'draw_card'
        else:
            self.txt_action = "keine Züge vorhanden"

    def btn_33_game_reload(self):
        self.txt_action = "reload Game..."
        self.localversion = 0

    # endregion

    # region game engine ###############################################################################################
    # actions
    def callback(self, event):

        def check_10(mycitynum, steps):  # action_10 -------------------------------------------------------------

            if self.this_player_turns['turn'] == 10 and \
                    mycitynum != self.all_player_pos[self.this_player_num] and \
                    steps <= self.this_player_turns['turns_left']:

                self.draw_city_highlight(self.get_player_path(mycitynum))

                self.this_player_turns['target'] = mycitynum
                self.this_player_turns['use'] = steps

                # server request
                self.value = {'player':     self.this_player_num,
                              'moveto':     self.this_player_turns['target'],
                              'usedcards':  []}
                self.action = 'player_move'
                # update game
                self.draw_city_highlight([])
                self.this_player_turns['turns_left'] -= self.this_player_turns['use']
                return ""
            else:
                self.draw_city_highlight([])
                return "Zug ungültig"

        if 8 < event.y < self.section_card:  # cardsection
            card_num = math.floor(float(event.x) / self.section_cardW)
            print("clicked at Card: " + str(card_num))  # TODO cardclick

            # action_101 --------------------------------------------------------------------------------------------
            if self.this_player_turns['turn'] == 101:
                self.value = {
                    'player': self.this_player_num,
                    'card': self.drawcard[0],
                    'move': card_num}
                if card_num < 7:
                    if card_num >= len(self.this_player_cards):
                        # print("add card")
                        # self.this_player_cards.append(self.drawcard[0])
                        del self.drawcard[0]
                        # self.display_game({"cards": 1})
                    else:
                        print("replace card")
                else:
                    print("dismiss card")
                self.this_player_turns['turn'] = 0
                self.action = 'move_card'

        elif self.section_field > event.y > self.section_card + 8:  # map -> find city
            # find city
            dist = 32000
            mycity = ""
            mycitynum = 0
            fy = (event.y - (self.section_card + 8))    # y-pos on field
            for c in self.city:
                if (0 + abs(c.get("posX") * self.section_game_w/100 - event.x) +
                        abs(c.get("posY") * self.section_game_w/100 / 2.125 - fy)) < dist:
                    dist = (abs(c.get("posX")*self.section_game_w/100 - event.x) +
                                abs(c.get("posY")*self.section_game_w/100 / 2.125 - fy))
                    mycity = c.get("name")
                    mycitynum = c.get("ID")
            if dist < (self.section_game_w/100 * 3):
                # print("clicked at City: " + mycity)  # TODO cityclick
                # print(self.this_player_turns)
                steps = len(self.get_player_path(mycitynum))

                # action_11 --------------------------------------------------------------------------------------------
                if self.this_player_turns['turn'] == 11 and mycitynum in self.this_player_cards:
                    self.this_player_turns['target'] = mycitynum
                    self.this_player_turns['use'] = 1
                    self.txt_action = "Direktflug nach " + mycity + ". (1 Aktion)"
                    self.draw_city_highlight([mycitynum])
                # action_12 --------------------------------------------------------------------------------------------
                if self.this_player_turns['turn'] == 12 and \
                        self.all_player_pos[self.this_player_num] in self.this_player_cards:
                    self.this_player_turns['target'] = mycitynum
                    self.this_player_turns['use'] = 1
                    self.txt_action = "Charterflug nach " + mycity + ". (1 Aktion)"
                    self.draw_city_highlight([mycitynum])
                # action_13 --------------------------------------------------------------------------------------------
                if self.this_player_turns['turn'] == 13 and \
                        self.city[self.all_player_pos[self.this_player_num]]['center']:
                    self.this_player_turns['target'] = mycitynum
                    self.this_player_turns['use'] = 1
                    self.txt_action = "Sonderflug nach " + mycity + ". (1 Aktion)"
                    self.draw_city_highlight([mycitynum])

                print("TURN EXECUTE")
                switcher = {
                    10: check_10,
                }
                func = switcher.get(self.this_player_turns['turn'], lambda m, s: "Zug ungültig")
                if self.this_player_turns['turns_left'] > 0:
                    self.txt_action = func(mycitynum, steps)  # execute

                    if self.this_player_turns["turns_left"] > 1:
                        self.txt_status = "Aktionsphase: " + str(
                            self.this_player_turns["turns_left"]) + " Aktionen verbleibend."
                    elif self.this_player_turns["turns_left"] == 1:
                        self.txt_status = "Aktionsphase: Eine Aktion verbleibend."
                    else:  # turn is over -> after-turn-phase
                        self.txt_action = ""
                        self.txt_status = "Nachschubpahse"
                        # self.this_player_turns["status"] = "supply_1"
                        self.value = self.this_player_num
                        self.action = 'draw_card'
                else:
                    self.txt_action = "keine Züge vorhanden"

        elif self.section_status > event.y > self.section_action + 8:
            print("statusbar")

        self.i_action.configure(text=self.txt_action)
        self.i_status.configure(text=self.txt_status)

    def init_update(self, args):
        print("init_update:", str(args))

        # update version
        self.localversion = args.get("v")

        # player_name / player role
        self.all_player_name = args.get("player")
        self.all_player_role = args.get("player_role")

        for p in range(0, 4):
            self.lbl_player_name[p].configure(text=self.all_player_name[p])
            self.lbl_player_func[p].configure(text=get_role_name(self.all_player_role[p]))
            if args.get("player_rdy")[p] == 1:
                self.lbl_player_name[p].configure(bg="SeaGreen1")
                self.lbl_player_func[p].configure(bg="SeaGreen1")

        self.action = 'getVersion'
        return False

    def game_update(self, args):
        # read data
        ###########################################################################
        # data = []
        # [ 0..47] = cities -> 5 values
        # [48..51] = playercards -> 7 values
        # [52] = stats -> 11 values {outbreak, inflvl, supplies,
        #                            inf0, inf1, inf2, inf3,
        #                            healing0, healing1, healing2, healing3}
        # [53] = player_pos -> 4 values
        ###########################################################################
        data = args.get("data")
        print("check update")

        if args.get("cur_player") == self.this_player_num and self.this_player_turns["status"] == "otherplayer":
            self.this_player_turns["status"] = "playeractive"
            self.this_player_turns["turns_left"] = 4

        updatelist = {'city': []}

        # cities
        for c in range(0, 48):
            akt_c = self.city[c]['i0'], self.city[c]['i1'], self.city[c]['i2'], self.city[c]['i3'],\
                    self.city[c]['center']
            if akt_c != (data[c][0], data[c][1], data[c][2], data[c][3], data[c][4]):
                self.city[c]['i0'] = data[c][0]
                self.city[c]['i1'] = data[c][1]
                self.city[c]['i2'] = data[c][2]
                self.city[c]['i3'] = data[c][3]
                self.city[c]['center'] = data[c][4]
                updatelist['city'].append(c)

        # cards
        if self.this_player_cards != data[self.this_player_num + 48]:
            self.this_player_cards = data[self.this_player_num + 48]
            updatelist['cards'] = 1

        # marker
        akt_m = self.outbreak, self.inflvl, self.supplies
        if akt_m != (data[52][0], data[52][1], data[52][2]):
            self.outbreak = data[52][0]
            self.inflvl = data[52][1]
            self.supplies = data[52][2]
            updatelist['marker1'] = 1

        count = 0
        for i in range(0, 4):
            if self.infection[i] != data[52][3 + i] or self.healing[i] != data[52][7 + i]:
                count = 1
            self.infection[i] = data[52][3 + i]
            self.healing[i] = data[52][7 + i]
        if count > 0:
            updatelist['marker2'] = 1

        # player pos
        if self.all_player_pos != data[53]:
            self.all_player_pos = data[53]
            updatelist['playerpos'] = 1

        self.display_game(updatelist)

        self.action = 'getVersion'
        # update version
        self.localversion = args.get("v")
        return False

    def recon_player(self, args):
        self.localversion = 0  # -> force update after recon
        self.this_player_name = args.get("player")[self.this_player_num]
        self.all_player_role = args.get("player_role")
        self.game_status = args.get("state")
        self.this_player_isrdy = 1

        return self.start_game

    def start_game(self):
        if self.this_player_isrdy:
            print("START_GAME")
            self.PREPframe.destroy()

            self.title("Pandemie")  # region UI

            user32 = ctypes.windll.user32
            # screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            # print(str(user32.GetSystemMetrics(0)) + "x" + str(user32.GetSystemMetrics(1)))
            win_x = user32.GetSystemMetrics(0) - 20
            win_y = user32.GetSystemMetrics(1) - 60

            win_x = int(win_x / 2)   # TODO DELETE THIS LINE ################################################################
            win_y = int(win_y / 2)   # TODO DELETE THIS LINE ################################################################

            self.geometry(str(win_x) + 'x' + str(win_y) + '+1+1')

            # print(str(win_x), str(win_y))

            # self.display_game(None)

            self.game_status = "GAME"
            self.action = 'get_update'
            self._update = True

            return True

        return False

    def lose_game(self):
        # TODO lose game
        print("You lose.")
        return True

    def win_game(self):
        # TODO win game
        print("WIN!")
        return True

    def player_set(self, args):
        print("PLAYER SET")

        # playernum
        self.this_player_num = args.get("player_num")    # [0..4]
        print("player_set: thisplayer_num:", str(self.this_player_num))

        # player_name / player role
        self.all_player_role = args.get("player_role")
        self.all_player_name = args.get("player")

        for p in range(0, 4):
            self.lbl_player_name[p].configure(text=self.all_player_name[p])
            self.lbl_player_func[p].configure(text=get_role_name(self.all_player_role[p]))

        if self.this_player_num > 3:
            print("to many players")
            self.lbl2.configure(text="Zu viele Spieler")
        else:
            self.btn_start.configure(state=NORMAL)
            self.lbl2.configure(text="Deine Rolle: " + get_role_name(self.all_player_role[self.this_player_num]))

            self.role_image.configure(image=self.img_char[self.all_player_role[self.this_player_num]])

        self.action = 'getVersion'
        return update_intervall

    def receive_card(self, args):
        if "cards" in args:
            self.this_player_cards = args.get('cards')[self.this_player_num]
            self.display_game({"cards": 1})

        if "card" in args:
            self.drawcard = args.get("card")
            print(self.drawcard)
            self.display_game({"cards": 1})
            self.draw_card_highlight()

        if len(self.drawcard) > 0:
            if self.drawcard[0] != 54:
                # new card
                #if len(self.drawcard) > 1:

                self.this_player_turns['turn'] = 101
                self.txt_action = "Ziehe Karte."

            else:
                # epidemie
                # TODO EPIDEMIE
                print("epidemie")
                self.txt_action = "Epidemie"
        else:
            self.draw_card_highlight(0)
            print("Infektionsphase")
            self.txt_action = ""
            self.txt_status = "Infektionsphase"

        self.i_action.configure(text=self.txt_action)  # update description for player
        self.i_status.configure(text=self.txt_status)  # update description for player

        self.action = 'getVersion'
        return True

    def gameclient(self, m_response, m_version):
        print("GameCient:", str(m_response), str(m_version))

        if m_response.get("response"):
            switcher = {
                "init_update": self.init_update,    # RESPONSE after request
                "player_set": self.player_set,      # RESPONSE after request
                "update": self.game_update,         # RESPONSE after request
                "recon": self.recon_player,         # RESPONSE after request
                "new_card": self.receive_card,      # RESPONSE after request
                "card_moved": self.receive_card,    # TODO test
                "START_GAME":  self.start_game,     # GLOBAL RESPONSE - STATE-CHANGE
                "LOSE_GAME": self.lose_game,        # GLOBAL RESPONSE - STATE-CHANGE
                "WIN_GAME": self.win_game,          # GLOBAL RESPONSE - STATE-CHANGE
            }
            func = switcher.get(m_response.get("response"), lambda: False)
            response = func(m_response)  # execute

            func = switcher.get(m_response.get("state"), lambda: False)
            state = func()

            if response or state:
                self._update = True
                self.set_after(self.task)

        else:
            if m_version is not None:
                if m_version != self.localversion:
                    self.value = self.this_player_num
                    switcher = {
                        'INIT':     "get_init_update",
                    }
                    self.action = switcher.get(self.game_status, "get_update")
                    self.set_after(self.task)
                else:
                    self.action = 'getVersion'
                    if self.game_status == "GAME":
                        self._update = False
                        self.update()
                        if self.old_window_h != self.winfo_height() or self.old_window_w != self.winfo_width():
                            self.display_game(None)
                            self.set_after(self.task)
            else:
                print("FAILURE: Game Engine - No response")
    # endregion

    def task(self):
        print("task")
        # create request
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
                            self.gameclient(message.get_response(), message.getVersion())
                    except Exception:
                        print(
                            "main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}",
                        )
                        message.close()
                # Check for a socket being monitored to continue.
                if not self.sel.get_map():
                    break
            # eval response
            # update = self.gameclient(message)
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")

        # loop within mainloop
        print("endloop")
        self.set_after(self.task)
        #self._task = self.after(update_intervall, self.task)


print("START")
app = Client()
app.mainloop()
