#!/usr/bin/env python3
# https://realpython.com/python-sockets/
# https://github.com/realpython/materials/tree/master/python-sockets-tutorial

import socket
import selectors
import traceback
import urllib.request
import random
import tkinter as tk
from tkinter import *
from threading import Thread
import math

from Pandemie import libserver

# Pandemie Server
#
#                                                                           Start Server UI
#                                                                                  │
# Server                                          <────────── start server ────────┤
#   -> init connection                                                             └ check Status every second
#       try to read own external IP (https://api.ipify.org/)
#       stores IP via PHP on moja.de
#   -> init game variable
#   -> START Game-Server
#       │
#     Status: "INIT"
#       ├ awaits request
#
#


class Server(Thread):
    def __init__(self):
        Thread.__init__(self)

        # region connection ############################################################################################
        self.host = socket.gethostname()
        self.port = 9999

        # system var
        self.request = {}
        self.sel = selectors.DefaultSelector()

        # try to read external IP from webservice and store on server via php-function
        self.external_ip = urllib.request.urlopen('https://api.ipify.org/').read().decode('utf8')
        link = 'http://moja.de/public/python/setip.php?ip=' + self.external_ip
        response = urllib.request.urlopen(link).read().decode('utf8').strip()
        if response == "done":
            print("IP successfully updated " + self.external_ip)
        else:
            print("FAILRE during IP-update")
        # setup conection
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind((self.host, self.port))
        lsock.listen()
        print("listening on", (self.host, self.external_ip, self.port))
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)
        # endregion

        # region gamevariables #########################################################################################
        self.serverversion = 0
        self.game_status = "INIT"
        self.player_name = ["", "", "", ""]
        self.player_role = [0, 0, 0, 0]
        self.player_rdy = [0, 0, 0, 0]
        self.player_cards = [[], [], [], []]    # in data2send included
        self.player_pos = [2, 2, 2, 2]

        self.current_player = 0

        # stats
        self.infection = [24, 24, 24, 24]
        self.outbreak = 0
        self.inflvl = 0
        self.newinfection = [2, 2, 2, 3, 3, 4]
        self.healing = [0, 0, 0, 0]         # 0 = active,  1 = healed,  2 = exterminated

        self.center = 5  # one in Atlanta + 5 => 6

        # Spielerkarten:
        # back:  back_c1.png
        # front: c1_##.png
        #  0-47: Stadtkarten
        # 48-52: Ereigniskarten
        #    53: Epidemiekarte
        #    54: BACK
        self.cardpile_player = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                                21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38,
                                39, 40, 41, 42, 43, 44, 45, 46, 47,
                                48, 49, 50, 51, 52]
        self.carddisposal_player = []
        self.card_epidemie = 53
        # Infektionskarten:
        # back:  back_c2.png
        # front: c2_##.png
        #  1-48: Stadtkarten
        self.cardpile_infection = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                                21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38,
                                39, 40, 41, 42, 43, 44, 45, 46, 47]
        self.carddisposal_infection = []

        # insert append remove count from 0 random.shuffle(x)

        # ID:       [1..48] continuous number
        # farbe:    [0..3]  color of infection
        # v1:       #       connection to other city. if = 0 -> no connection
        # v2:
        # v3
        # v4:
        # v5:
        # v6:
        # i0:       [0..2]  number of infections, color 0, default: 0
        # i1:       [0..2]  number of infections, color 1, default: 0
        # i2:       [0..2]  number of infections, color 2, default: 0
        # i3:       [0..2]  number of infections, color 3, default: 0
        # center':  bool    is a center in the city, default:0, Atlanta (ID: 3): 1
        # name':    str     eg. 'San Francisco'
        #
        self.city = [{'ID':  0, 'farbe': 0, 'v1':  2, 'v2': 13, 'v3': 40, 'v4': 47, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  5864, 'name': 'San Francisco'},
                     {'ID':  1, 'farbe': 0, 'v1':  1, 'v2': 13, 'v3': 14, 'v4':  3, 'v5':  4, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  9121, 'name': 'Chicago'},
                     {'ID':  2, 'farbe': 0, 'v1':  2, 'v2':  6, 'v3': 15, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 1, 'pop':  4715, 'name': 'Atlanta'},
                     {'ID':  3, 'farbe': 0, 'v1':  2, 'v2':  6, 'v3':  5, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  3429, 'name': 'Montréal'},
                     {'ID':  4, 'farbe': 0, 'v1':  4, 'v2':  6, 'v3':  7, 'v4':  8, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 20464, 'name': 'New York'},
                     {'ID':  5, 'farbe': 0, 'v1':  5, 'v2':  4, 'v3':  3, 'v4': 15, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  4679, 'name': 'Washington'},
                     {'ID':  6, 'farbe': 0, 'v1':  5, 'v2': 20, 'v3': 25, 'v4':  9, 'v5':  8, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  5427, 'name': 'Madrid'},
                     {'ID':  7, 'farbe': 0, 'v1':  5, 'v2':  7, 'v3':  9, 'v4': 10, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  8586, 'name': 'London'},
                     {'ID':  8, 'farbe': 0, 'v1':  8, 'v2':  7, 'v3': 25, 'v4': 11, 'v5': 10, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 10755, 'name': 'Paris'},
                     {'ID':  9, 'farbe': 0, 'v1':  8, 'v2':  9, 'v3': 11, 'v4': 12, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':   575, 'name': 'Essen'},
                     {'ID': 10, 'farbe': 0, 'v1': 10, 'v2':  9, 'v3': 27, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  5232, 'name': 'Mailand'},
                     {'ID': 11, 'farbe': 0, 'v1': 10, 'v2': 27, 'v3': 28, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  4879, 'name': 'St. Petersburg'},
                     {'ID': 12, 'farbe': 1, 'v1': 48, 'v2': 14, 'v3':  2, 'v4':  1, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 14900, 'name': 'Los Angeles'},
                     {'ID': 13, 'farbe': 1, 'v1': 13, 'v2': 17, 'v3': 16, 'v4': 15, 'v5':  2, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 19463, 'name': 'Mexico Stadt'},
                     {'ID': 14, 'farbe': 1, 'v1': 14, 'v2': 16, 'v3':  6, 'v4':  3, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  5582, 'name': 'Miami'},
                     {'ID': 15, 'farbe': 1, 'v1': 14, 'v2': 17, 'v3': 19, 'v4': 20, 'v5': 15, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  8102, 'name': 'Bogotá'},
                     {'ID': 16, 'farbe': 1, 'v1': 14, 'v2': 18, 'v3': 16, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 10479, 'name': 'Lima'},
                     {'ID': 17, 'farbe': 1, 'v1': 17, 'v2':  0, 'v3':  0, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  6015, 'name': 'Santiago'},
                     {'ID': 18, 'farbe': 1, 'v1': 16, 'v2': 20, 'v3':  0, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 13639, 'name': 'Buenos Aires'},
                     {'ID': 19, 'farbe': 1, 'v1': 16, 'v2': 19, 'v3': 21, 'v4':  7, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 20186, 'name': 'Sao Paulo'},
                     {'ID': 20, 'farbe': 1, 'v1': 20, 'v2': 22, 'v3': 24, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 11547, 'name': 'Lagos'},
                     {'ID': 21, 'farbe': 1, 'v1': 21, 'v2': 23, 'v3': 24, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  9046, 'name': 'Kinshasa'},
                     {'ID': 22, 'farbe': 1, 'v1': 22, 'v2': 24, 'v3':  0, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  3888, 'name': 'Johannisburg'},
                     {'ID': 23, 'farbe': 1, 'v1': 21, 'v2': 22, 'v3': 23, 'v4': 26, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  4887, 'name': 'Khartum'},
                     {'ID': 24, 'farbe': 2, 'v1':  7, 'v2': 26, 'v3': 27, 'v4':  9, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  2946, 'name': 'Algier'},
                     {'ID': 25, 'farbe': 2, 'v1': 25, 'v2': 24, 'v3': 30, 'v4': 29, 'v5': 27, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 14718, 'name': 'Kairo'},
                     {'ID': 26, 'farbe': 2, 'v1': 25, 'v2': 26, 'v3': 29, 'v4': 28, 'v5': 12, 'v6': 11, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 13576, 'name': 'Istanbul'},
                     # TODO REMOVE CENTER FROM MOSKAU ##############################################################################################################################################
                     {'ID': 27, 'farbe': 2, 'v1': 12, 'v2': 27, 'v3': 31, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 1, 'pop': 15512, 'name': 'Moskau'},
                     {'ID': 28, 'farbe': 2, 'v1': 27, 'v2': 26, 'v3': 30, 'v4': 32, 'v5': 31, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  6204, 'name': 'Bagdad'},
                     {'ID': 29, 'farbe': 2, 'v1': 26, 'v2': 32, 'v3': 29, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  5037, 'name': 'Riad'},
                     {'ID': 30, 'farbe': 2, 'v1': 28, 'v2': 29, 'v3': 32, 'v4': 34, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  7419, 'name': 'Teheran'},
                     {'ID': 31, 'farbe': 2, 'v1': 29, 'v2': 30, 'v3': 33, 'v4': 34, 'v5': 31, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 20711, 'name': 'Karatschi'},
                     {'ID': 32, 'farbe': 2, 'v1': 32, 'v2': 35, 'v3': 34, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 16910, 'name': 'Mumbai'},
                     {'ID': 33, 'farbe': 2, 'v1': 31, 'v2': 32, 'v3': 33, 'v4': 35, 'v5': 36, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 22242, 'name': 'Delhi'},
                     {'ID': 34, 'farbe': 2, 'v1': 33, 'v2': 45, 'v3': 41, 'v4': 36, 'v5': 34, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  8865, 'name': 'Chennai'},
                     {'ID': 35, 'farbe': 2, 'v1': 34, 'v2': 35, 'v3': 41, 'v4': 42, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 14374, 'name': 'Kalkutta'},
                     {'ID': 36, 'farbe': 3, 'v1': 38, 'v2': 39, 'v3':  0, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 17311, 'name': 'Peking'},
                     {'ID': 37, 'farbe': 3, 'v1': 37, 'v2': 39, 'v3': 40, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 22547, 'name': 'Seoul'},
                     {'ID': 38, 'farbe': 3, 'v1': 37, 'v2': 42, 'v3': 43, 'v4': 40, 'v5': 38, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 13482, 'name': 'Shanghai'},
                     {'ID': 39, 'farbe': 3, 'v1': 38, 'v2': 39, 'v3': 44, 'v4':  1, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 13189, 'name': 'Tokyo'},
                     {'ID': 40, 'farbe': 3, 'v1': 35, 'v2': 45, 'v3': 46, 'v4': 42, 'v5': 36, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  7151, 'name': 'Bangkok'},
                     {'ID': 41, 'farbe': 3, 'v1': 36, 'v2': 41, 'v3': 46, 'v4': 47, 'v5': 43, 'v6': 39, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  7106, 'name': 'Hong Kong'},
                     {'ID': 42, 'farbe': 3, 'v1': 42, 'v2': 47, 'v3': 44, 'v4': 39, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  8338, 'name': 'Taipeh'},
                     {'ID': 43, 'farbe': 3, 'v1': 40, 'v2': 43, 'v3':  0, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  2871, 'name': 'Osaka'},
                     {'ID': 44, 'farbe': 3, 'v1': 35, 'v2': 48, 'v3': 46, 'v4': 41, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 26063, 'name': 'Jakarta'},
                     {'ID': 45, 'farbe': 3, 'v1': 45, 'v2': 47, 'v3': 42, 'v4': 41, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  8314, 'name': 'Ho-Chi-MinH-Stadt'},
                     {'ID': 46, 'farbe': 3, 'v1': 46, 'v2': 48, 'v3':  1, 'v4': 43, 'v5': 42, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop': 20767, 'name': 'Manila'},
                     {'ID': 47, 'farbe': 3, 'v1': 47, 'v2': 45, 'v3': 13, 'v4':  0, 'v5':  0, 'v6':  0, 'i0': 0, 'i1': 0, 'i2': 0, 'i3': 0, 'center': 0, 'pop':  3785, 'name': 'Sydney'}]
        # endregion

        self.start()

    # region functions #################################################################################################
    def data2send(self):
        ##########################################################
        data = []
        # [ 0..47] = cities -> 5 values
        # [48..51] = playercards -> x values
        # [52] = stats -> 11 values {outbreak, inflvl, supplies,
        #                            inf0, inf1, inf2, inf3,
        #                            healing0, healing1, healing2, healing3}
        # [53] = player_pos
        ##########################################################
        for c in self.city:
            line = [c.get('i0'), c.get('i1'), c.get('i2'), c.get('i3'), c.get('center')]
            data.append(line)

        for p in range(0, 4):
            # line = []
            # for c in range(0, 7):
            #     if len(self.player_cards[p]) > c:
            #         line.append(self.player_cards[p][c])
            #     else:
            #         line.append(0)
            # data.append(line)
            data.append(self.player_cards[p])

        line = [self.outbreak, self.inflvl, len(self.cardpile_player)]
        for i in self.infection:
            line.append(i)
        for h in self.healing:
            line.append(h)
        data.append(line)

        data.append(self.player_pos)
        # print(data)
        return data

    def set_player_role(self):
        role = random.randint(0, 7)
        check = True
        while check:
            check = False
            for r in self.player_role:
                if role == r:
                    check = True
                    role = random.randint(0, 7)
        return role

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        # print("accepted connection from", addr)
        conn.setblocking(False)
        message = libserver.Message(self.sel, conn, addr)
        self.sel.register(conn, selectors.EVENT_READ, data=message)
    # endregion

    # region SERVER GAME CLIENT ########################################################################################
    def actions(self, argument):
        self.request = argument
        switcher = {
            "getVersion":       self.get_version,       # Init Game
            "player_signin":    self.set_player,        # Init Game
            "get_init_update":  self.get_init_update,   # update Game-Preparation-Data to client
            "player_rdy":       self.player_is_rdy,     # Init Game
            "recon":            self.recon_player,      # reconnect Player
            "get_update":       self.get_update,        # Main Game
            "player_move":      self.player_move,       # Main Game
            "draw_card":        self.deal_card,         # Main Game
            "get_infection":    self.deal_infection,
            "update_cards":     self.update_cards,
        }
        # Get the function from switcher dictionary
        func = switcher.get(argument.get("action"), lambda: None)
        # execute
        output = func()

        # default value if action is not known
        if output is None:
            output = {"result": "action not known"}
        return output

    # global ----------------------------------------------------------------------------------------------------------#
    def get_version(self):
        content = {"v": self.serverversion, "p": self.current_player}
        return content

    # INIT ------------------------------------------------------------------------------------------------------------#
    def get_init_update(self):
        content = {"response":      "init_update",
                   "v":             self.serverversion,
                   "player":        self.player_name,
                   "player_role":   self.player_role,
                   "player_rdy":    self.player_rdy,
                   "state":         self.game_status
                   }
        return content

    def set_player(self):
        self.serverversion += 1

        newname = self.request.get("value")

        n = 0
        while n < len(self.player_name):
            print(str(n) + " " + self.player_name[n])
            if self.player_name[n] != "":
                n = n + 1
            else:
                break
        if n < len(self.player_name):
            self.player_name[n] = newname
            self.player_role[n] = self.set_player_role()

        content = {"response": "player_set",
                   "v": self.serverversion,
                   "player_num": n,
                   "player":        self.player_name,
                   "player_role":   self.player_role,
                   "player_rdy":    self.player_rdy,
                   }
        return content

    def player_is_rdy(self):
        p = self.request.get("value")
        print("Player " + str(p) + " is ready")
        self.player_rdy[p] = 1
        return self.get_init_update()

    def recon_player(self):
        content = {"response": "recon",
                   "player": self.player_name,
                   "player_role": self.player_role,
                   "state": self.game_status
                   }
        return content

    def startgame(self, lvl):
        # shuffle cardpiles
        random.shuffle(self.cardpile_player)
        random.shuffle(self.cardpile_infection)

        # start infection
        # Städte infizieren -> Karten auf Ablage
        #   3 x mit 3
        #   3 x mit 2
        #   3 x mit 1
        for x in range(0, 3):
            for xx in range(0, 3):
                city = self.cardpile_infection[0]
                self.carddisposal_infection.append(city)
                del self.cardpile_infection[0]

                inf = self.city[city].get('farbe')
                self.infection[inf] -= x + 1

                self.city[city]['i'+str(inf)] = x + 1

        print(self.city)

        # deal cards
        player_count = 0
        for p in self.player_name:
            if p != "":
                player_count += 1

        # todo del comment
        #player_count = 3  # TODO  TEMP !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        # prepare player draw cards
        # lvl = 1: easy   -> 4 epidemie cards
        # lvl = 2: normal -> 5 epidemie cards
        # lvl = 3: hard   -> 6 epidemie cards
        pop = 0

        for p in range(0, player_count):
            for c in range(0, 6 - player_count):
                card = self.cardpile_player[0]
                self.player_cards[p].append(card)
                del self.cardpile_player[0]

                # set first player
                if card <= 48:
                    # print("pop", str(p), str(self.city[card-1].get('pop')))
                    if self.city[c].get('pop') > pop:
                        pop = self.city[c].get('pop')
                        self.current_player = p  # set start player

        print("Player cards:", self.player_cards)
        print("Start Player:", str(self.current_player))

        # Epidemiekarten 'gleichmäßig' in Stapel mischen
        #   4 = leicht
        #   5 = standard
        #   6 = Heldenstufe
        pile_part = []
        part_size = math.floor(len(self.cardpile_player) / (lvl + 3))

        for parts in range(0, lvl+3):
            pile_part.append([])
            for cards in range(0, part_size):
                pile_part[parts].append(self.cardpile_player[0])
                del self.cardpile_player[0]
            pile_part[parts].append(self.card_epidemie)

        while len(self.cardpile_player) > 0:
            pile_part[random.randint(0, lvl + 2)].append(self.cardpile_player[0])
            del self.cardpile_player[0]

        for piles in pile_part:
            random.shuffle(piles)

        for piles in pile_part:
            for c in range(0, len(piles)):
                self.cardpile_player.append(piles[c])

        self.game_status = "START_GAME"
        self.serverversion += 1
        print("START GAME")

    # MAINGAME --------------------------------------------------------------------------------------------------------#
    def get_update(self):
        # todo update only relevant parts

        content = {"response":  "update",
                   "v":          self.serverversion,
                   "cur_player": self.current_player,
                   "data":       self.data2send(),
                   }
        return content

    def player_move(self):
        self.serverversion += 1
        movep = self.request.get("value")
        # 'player': self.this_player_num,
        # 'moveto': self.this_player_turns['target'],
        # 'usedcards': []

        self.player_pos[movep['player']] = movep['moveto']
        for card in movep['usedcards']:
            self.carddisposal_player.append(card)
            self.player_cards[movep['player']].remove(card)

        # todo do stuff
        return self.get_update()

    def deal_card(self):
        self.serverversion += 1
        # val = self.request.get("value")
        if len(self.cardpile_player) > 1:       # check pile
            new_card = self.cardpile_player[0], self.cardpile_player[1]  # draw card
            del self.cardpile_player[0]         # remove card from pile
            del self.cardpile_player[0]         # remove card from pile
            content = {"response": "new_cards",
                       "new_cards": new_card
                       }
            return content
        else:  # last card is drawn -> YOU LOSE -----------------------------------------------
            self.game_status = "LOSE"
            return self.get_update()

    def deal_infection(self):
        self.serverversion += 1
        new_card = []
        num = self.newinfection[self.inflvl] if self.inflvl < 6 else 4
        print(num)
        for c in range(0, num):
            new_card.append(self.cardpile_infection[0])
            self.carddisposal_infection.append(self.cardpile_infection[0])
            del self.cardpile_infection[0]
        content = {"response": "new_cards",
                   "new_inf": new_card
                   }
        return content

    def update_cards(self):
        # self.serverversion += 1
        update = self.request.get("value")
        self.player_cards[update.get('player')] = update.get('cards')
        for c in update.get('burn'):
            self.carddisposal_player.append(c)
        return self.get_version()


    # endregion

    # region mainloop ##################################################################################################
    def run(self):
        try:
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                            if mask == 1:
                                req = message.get_request()
                                if req.get("action"):
                                    message.set_response(self.actions(req))
                        except Exception:
                            print(
                                "main: error: exception for",
                                f"{message.addr}:\n{traceback.format_exc()}",
                            )
                            message.close()
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.sel.close()
    # endregion


class ServerInterface(tk.Tk):
    def __init__(self):

        self.player = ["", "", "", ""]
        self.player_rdy = [0, 0, 0, 0]

        tk.Tk.__init__(self)

        self.title("Pandemie | Server")
        self.geometry("150x300")

        self.lblstatus = Label(self, text="Status", font="Helvetica 12")
        self.lblstatus.pack(fill=X, pady=10)
        self.lbl_plr_0 = Label(self, text="Player 1", font="Helvetica 10")
        self.lbl_plr_0.pack(fill=X)
        self.lbl_plr_1 = Label(self, text="Player 2", font="Helvetica 10")
        self.lbl_plr_1.pack(fill=X)
        self.lbl_plr_2 = Label(self, text="Player 3", font="Helvetica 10")
        self.lbl_plr_2.pack(fill=X)
        self.lbl_plr_3 = Label(self, text="Player 4", font="Helvetica 10")
        self.lbl_plr_3.pack(fill=X)

        Label(self, text="Schwierigkeit:", justify=LEFT).pack(anchor=W, pady=(10, 0), padx=10)

        self.v = IntVar()
        self.v.set(2)

        lvl = [
            ("einfach", 1),
            ("normal", 2),
            ("experte", 3)
        ]

        for txt, val in lvl:
            Radiobutton(self,
                        text=txt,
                        padx=20,
                        variable=self.v,
                value=val).pack(anchor=W)

        self.btn_startgame = Button(self, text='Start Game', command=self.btn_startgame)
        self.btn_startgame.pack(fill=X, pady=10, padx=10)

        self.myserver = Server()
        self.gui_loop()

    def btn_startgame(self):
        self.btn_startgame.configure(text="game running", state=DISABLED)
        self.myserver.startgame(self.v.get())

    def gui_loop(self):
        self.lblstatus.configure(text=self.myserver.external_ip)

        self.player = self.myserver.player_name
        self.player_rdy = self.myserver.player_rdy

        if self.player[0] != "":
            self.lbl_plr_0.configure(text=self.player[0])
        if self.player_rdy[0]:
            self.lbl_plr_0.configure(bg="SeaGreen1")

        if self.player[1] != "":
            self.lbl_plr_1.configure(text=self.player[1])
        if self.player_rdy[1]:
            self.lbl_plr_1.configure(bg="SeaGreen1")

        if self.player[2] != "":
            self.lbl_plr_2.configure(text=self.player[2])
        if self.player_rdy[2]:
            self.lbl_plr_2.configure(bg="SeaGreen1")

        if self.player[3] != "":
            self.lbl_plr_2.configure(text=self.player[3])
        if self.player_rdy[3]:
            self.lbl_plr_2.configure(bg="SeaGreen1")

        self.after(1000, self.gui_loop)


if __name__ == '__main__':
    app = ServerInterface()  # start UI -> ui starts server
    app.mainloop()
