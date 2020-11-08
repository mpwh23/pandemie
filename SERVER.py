#!/usr/bin/env python3
# https://realpython.com/python-sockets/
# https://github.com/realpython/materials/tree/master/python-sockets-tutorial

import socket
import selectors
import traceback
import urllib.request
import random
import tkinter as tk
from tkinter import ttk
from tkinter import *
from threading import Thread
import math
import inspect

from Pandemie import libserver


AM_DEBUG_OUTPUT = True


def _print(*args):
    if AM_DEBUG_OUTPUT:
        line = ""
        for txt in args:
            line = line + " " + str(txt)
        if len(args) > 0:
            line += " > "
        print(line + inspect.stack()[1].__getattribute__("function"))


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
            print("FAILURE during IP-update")
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
        self.server_version = 0
        self.server_history = {}
        self.server_history_length = 150

        self.game_STATE = "INIT"
        self.reason = ""
        self.current_player = (0, 0)
        self.player_name = ["", "", "", ""]
        self.player_role = [0, 0, 0, 0]
        self.player_rdy = [0, 0, 0, 0]
        self.player_cards = [[], [], [], []]
        self.player_pos = [0, 0, 0, 0]

        self.card_exchange = {'status': "", 's': 9, 'c': 99, 'r': 9, 'b': 99, 'd': 0}
        self.special_val = {'r3': 0, 'a50': []}

        # stats
        self.infection = [24, 24, 24, 24]
        self.outbreak = 0
        self.inflvl = 0
        self.healing = [0, 0, 0, 0]         # 0 = active,  1 = healed,  2 = exterminated

        self.visual = {}

        # working var
        self.newinfection = [2, 2, 2, 3, 3, 4]
        self.skipinfection = False
        self.error_message = ""

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
        # d:         [0..3] color of desease / infection
        # con:              connection to other city.
        # i0:       [0..2]  number of infections, color 0, default: 0
        # i1:       [0..2]  number of infections, color 1, default: 0
        # i2:       [0..2]  number of infections, color 2, default: 0
        # i3:       [0..2]  number of infections, color 3, default: 0
        # center':  bool    is a center in the city, default:0, Atlanta (ID: 3): 1
        # name':    str     eg. 'San Francisco'
        #

        self.city = [  # d = disease, i = infection
            {'ID':  0, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  5864, 'con': [1, 12, 39, 46],          'name': 'San Francisco'},
            {'ID':  1, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  9121, 'con': [0, 12, 13,  2,  3],      'name': 'Chicago'},
            {'ID':  2, 'd': 0, 'i': [0, 0, 0, 0], 'c': 1, 'pop':  4715, 'con': [1,  5, 14],              'name': 'Atlanta'},
            {'ID':  3, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  3429, 'con': [1,  5,  4],              'name': 'Montréal'},
            {'ID':  4, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 20464, 'con': [3,  5,  6,  7],          'name': 'New York'},
            {'ID':  5, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  4679, 'con': [ 4,  3,  2, 14],         'name': 'Washington'},
            {'ID':  6, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  5427, 'con': [ 4, 19, 24,  8,  7],     'name': 'Madrid'},
            {'ID':  7, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  8586, 'con': [ 4,  6,  8,  9],         'name': 'London'},
            {'ID':  8, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 10755, 'con': [ 7,  6, 24, 10,  9],     'name': 'Paris'},
            {'ID':  9, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop':   575, 'con': [ 7,  8, 10, 11],         'name': 'Essen'},
            {'ID': 10, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  5232, 'con': [ 9,  8, 26],             'name': 'Mailand'},
            {'ID': 11, 'd': 0, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  4879, 'con': [ 9, 26, 27],             'name': 'St. Petersburg'},
            {'ID': 12, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 14900, 'con': [47, 13,  1,  0],         'name': 'Los Angeles'},
            {'ID': 13, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 19463, 'con': [12, 16, 15, 14,  1],     'name': 'Mexico Stadt'},
            {'ID': 14, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  5582, 'con': [13, 15,  5,  2],         'name': 'Miami'},
            {'ID': 15, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  8102, 'con': [13, 16, 18, 19, 14],     'name': 'Bogotá'},
            {'ID': 16, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 10479, 'con': [13, 17, 15],             'name': 'Lima'},
            {'ID': 17, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  6015, 'con': [16],                     'name': 'Santiago'},
            {'ID': 18, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 13639, 'con': [15, 19],                 'name': 'Buenos Aires'},
            {'ID': 19, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 20186, 'con': [15, 18, 20,  6],         'name': 'Sao Paulo'},
            {'ID': 20, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 11547, 'con': [19, 21, 23],             'name': 'Lagos'},
            {'ID': 21, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  9046, 'con': [20, 22, 23],             'name': 'Kinshasa'},
            {'ID': 22, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  3888, 'con': [21, 23],                 'name': 'Johannisburg'},
            {'ID': 23, 'd': 1, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  4887, 'con': [20, 21, 22, 25],         'name': 'Khartum'},
            {'ID': 24, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  2946, 'con': [ 6, 25, 26,  8],         'name': 'Algier'},
            {'ID': 25, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 14718, 'con': [24, 23, 29, 28, 26],     'name': 'Kairo'},
            {'ID': 26, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 13576, 'con': [24, 25, 28, 27, 11, 10], 'name': 'Istanbul'},
            {'ID': 27, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 15512, 'con': [11, 26, 30],             'name': 'Moskau'},
            {'ID': 28, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  6204, 'con': [26, 25, 29, 31, 30],     'name': 'Bagdad'},
            {'ID': 29, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  5037, 'con': [25, 31, 28],             'name': 'Riad'},
            {'ID': 30, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  7419, 'con': [27, 28, 31, 33],         'name': 'Teheran'},
            {'ID': 31, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 20711, 'con': [28, 29, 32, 33, 30],     'name': 'Karatschi'},
            {'ID': 32, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 16910, 'con': [31, 34, 33],             'name': 'Mumbai'},
            {'ID': 33, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 22242, 'con': [30, 31, 32, 34, 35],     'name': 'Delhi'},
            {'ID': 34, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  8865, 'con': [32, 44, 40, 35, 33],     'name': 'Chennai'},
            {'ID': 35, 'd': 2, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 14374, 'con': [33, 34, 40, 41],         'name': 'Kalkutta'},
            {'ID': 36, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 17311, 'con': [37, 38],                 'name': 'Peking'},
            {'ID': 37, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 22547, 'con': [36, 38, 39],             'name': 'Seoul'},
            {'ID': 38, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 13482, 'con': [36, 41, 42, 39, 37],     'name': 'Shanghai'},
            {'ID': 39, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 13189, 'con': [37, 38, 43,  0],         'name': 'Tokyo'},
            {'ID': 40, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  7151, 'con': [34, 44, 45, 41, 35],     'name': 'Bangkok'},
            {'ID': 41, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  7106, 'con': [35, 40, 45, 46, 42, 38], 'name': 'Hong Kong'},
            {'ID': 42, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  8338, 'con': [41, 46, 43, 38],         'name': 'Taipeh'},
            {'ID': 43, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  2871, 'con': [39, 42],                 'name': 'Osaka'},
            {'ID': 44, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 26063, 'con': [34, 47, 45, 40],         'name': 'Jakarta'},
            {'ID': 45, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  8314, 'con': [44, 46, 41, 40],         'name': 'Ho-Chi-MinH-Stadt'},
            {'ID': 46, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop': 20767, 'con': [45, 47,  0, 42, 41],     'name': 'Manila'},
            {'ID': 47, 'd': 3, 'i': [0, 0, 0, 0], 'c': 0, 'pop':  3785, 'con': [46, 44, 12],             'name': 'Sydney'}]
        # endregion

    # region functions #################################################################################################
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

    def version(self, key, *args):

        switcher = {
            'player_cards':     ('CP', self.player_cards),
            'card_exchange':    ('CE', self.card_exchange),
            'special_val':      ('C3', self.special_val),
            'outbreak':         ('SO', self.outbreak),
            'inflvl':           ('SL', self.inflvl),
            'supply':           ('SS', len(self.cardpile_player)),
            'infection':        ('SI', self.infection),
            'healing':          ('SH', self.healing),
            'player_pos':       ('PP', self.player_pos),
            'current_player':   ('PC', self.current_player),
            'player_name':      ('PN', self.player_name),
            'player_role':      ('PR', self.player_role),
            'player_rdy':       ('PS', self.player_rdy),
            'STATE':            ('S', {'s': self.game_STATE, 'r': self.reason}),
            'VI':               ('VI', self.visual)
        }

        if key == 'city':
            short_key = 'C'
            value = {args[0]: [self.city[args[0]].get('i')[0],
                               self.city[args[0]].get('i')[1],
                               self.city[args[0]].get('i')[2],
                               self.city[args[0]].get('i')[3],
                               self.city[args[0]].get('c')]}
        else:
            short_key = switcher.get(key, lambda: None)[0]
            value = switcher.get(key, lambda: None)[1]

        self.server_history[self.server_version] = {short_key: value}

        # cleanup
        if self.server_version > self.server_history_length:
            for cleanup in range(0, self.server_version - self.server_history_length):
                if cleanup in self.server_history:
                    del self.server_history[cleanup]

        self.server_version += 1

    def get_update(self):
        old = self.request.get('value').get('v')
        newupdate = {"R": "update",
                     "v": self.server_version}

        if old in self.server_history:
            for item in range(old, self.server_version):
                key = next(iter(self.server_history[item]))
                if key != 'C' or 'C' not in newupdate:
                    newupdate[key] = self.server_history[item][key]
                else:  # append city
                    c_key = next(iter(self.server_history[item][key]))
                    newupdate[key][c_key] = self.server_history[item][key][c_key]

            return newupdate
        else:  # complete update
            newupdate['CP'] = self.player_cards
            newupdate['CE'] = self.card_exchange
            newupdate['C3'] = self.special_val
            newupdate['SO'] = self.outbreak
            newupdate['SL'] = self.inflvl
            newupdate['SS'] = len(self.cardpile_player)
            newupdate['SI'] = self.infection
            newupdate['SH'] = self.healing
            newupdate['PP'] = self.player_pos
            newupdate['PC'] = self.current_player
            newupdate['PN'] = self.player_name
            newupdate['PR'] = self.player_role
            newupdate['PS'] = self.player_rdy
            newupdate['S'] = {'s': self.game_STATE, 'r': self.reason}
            newupdate['C'] = {}
            for num, c in enumerate(self.city):
                newupdate['C'][num] = [c.get('i')[0], c.get('i')[1], c.get('i')[2], c.get('i')[3], c.get('c')]

            return newupdate
    # endregion

    # region SERVER GAME CLIENT ########################################################################################
    def actions(self, argument):

        self.request = argument

        switcher = {
            "getVersion":           self.get_version,               # Init Game
            "player_signin":        self.set_player,                # Init Game
            "get_init_update":      self.get_init_update,           # update Game-Preparation-Data to client
            "player_rdy":           self.player_is_rdy,             # Init Game
            "recon":                self.recon_player,              # reconnect Player
            "get_update":           self.get_update,                # Main Game
            "player_move":          self.player_move,               # Main Game
            "draw_playercard":      self.deal_cards_player,         # Main Game
            "draw_infcard":         self.deal_card_infection,
            "draw_epidemiecard":    self.deal_card_epidemie,
            "center":               self.update_center,
            "heal":                 self.healdisease,
            "card_exchange":        self.deal_card_exchange,
            "update_cards":         self.update_cards,
            "update_inf":           self.update_infection,
            "turn_over":            self.set_next_player,
            "error":                self.print_error,
            "actioncard":           self.manage_actioncard,
            "role3":                self.krisenmanager,
            "end_turn":             self.endturn,

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
        content = {"v": self.server_version}
        return content

    def print_error(self):
        print("ERROR ------", str(self.request.get("value").get('e')))
        self.error_message = self.request.get("value").get('e')

        return self.get_update()

    def turnsleft(self, sub):
        self.current_player = (self.current_player[0], self.current_player[1] + sub)
        self.version("current_player")

    # region ------ INIT ----------------------------------------------------------------------------------------------#
    def get_init_update(self):
        content = {"R":             "init_update",
                   "v":             self.server_version,
                   "player":        self.player_name,
                   "player_role":   self.player_role,
                   "player_rdy":    self.player_rdy,
                   "state":         self.game_STATE
                   }
        return content

    def set_player(self):

        newname = self.request.get("value").get('player_name')

        n = 0
        while n < len(self.player_name):
            # print(str(n) + " " + self.player_name[n])
            if self.player_name[n] != "":
                n = n + 1
            else:
                break
        if n < len(self.player_name):
            self.player_name[n] = newname
            self.player_role[n] = self.set_player_role()
            self.version("player_name")
            self.version("player_role")

        content = {"R":             "player_set",
                   "v":             self.server_version,
                   "player_num":    n,
                   "player":        self.player_name,
                   "player_role":   self.player_role,
                   "player_rdy":    self.player_rdy,
                   }
        return content

    def player_is_rdy(self):
        p = self.request.get("value").get("player_num")
        print("Player " + str(p) + " is ready")
        self.player_rdy[p] = 1
        self.version("player_rdy")
        return self.get_init_update()

    def recon_player(self):
        content = {"R": "recon",
                   "player": self.player_name,
                   "player_role": self.player_role,
                   "state": self.game_STATE,
                   "reason": self.reason
                   }
        return content

    def startgame(self, lvl):
        # shuffle cardpiles
        random.shuffle(self.cardpile_player)
        random.shuffle(self.cardpile_infection)

        # start infection
        # Städte infizieren -> Karten auf Ablage
        #   3 x 3, 3 x 2, 3 x 1
        for x in range(0, 3):
            for xx in range(0, 3):
                city = self.cardpile_infection[0]
                self.carddisposal_infection.append(city)
                del self.cardpile_infection[0]

                disease = self.city[city].get('d')
                self.infection[disease] -= x + 1

                self.city[city]['i'][disease] = x + 1
                self.version("city", city)

        # deal cards
        player_count = 0
        for p in self.player_name:
            if p != "":
                player_count += 1

        # prepare player draw cards
        # lvl = 1: easy   -> 4 epidemie cards
        # lvl = 2: normal -> 5 epidemie cards
        # lvl = 3: hard   -> 6 epidemie cards
        pop = 0

        for p in range(0, player_count):
            self.player_pos[p] = 2
            for c in range(0, 6 - player_count):
                card = self.cardpile_player[0]
                self.player_cards[p].append(card)
                del self.cardpile_player[0]

                # set first player
                if card <= 48:
                    # print("pop", str(p), str(self.city[card-1].get('pop')))
                    if self.city[c].get('pop') > pop:
                        pop = self.city[c].get('pop')
                        self.current_player = (p, 4)  # set start player

        _print("Player cards:", self.player_cards)
        _print("Start Player:", str(self.current_player))

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

        self.game_STATE = "GAME"

        self.version("infection")
        self.version("player_pos")
        self.version("player_cards")
        self.version("supply")
        self.version("current_player")
        self.version("STATE")

        print("START GAME")
    # endregion

    # region ------ MAINGAME ------------------------------------------------------------------------------------------#
    def player_move(self):

        movep = self.request.get("value")
        # 'player': self.this_player_num,
        # 'moveto': self.this_player_turns['target'],
        # 'usedcards': []

        # player, from, to
        self.visual = {'move': [movep['player'], self.player_pos[movep['moveplayer']], movep['moveto']]}
        self.version("VI")

        self.player_pos[movep['moveplayer']] = movep['moveto']
        if 'steps' in movep:
            self.turnsleft(-movep['steps'])
        self.version("player_pos")

        for card in movep['usedcards']:
            if card in self.player_cards[movep['player']]:
                self.player_cards[movep['player']].remove(card)
                self.carddisposal_player.append(card)
                self.version("player_cards")
            else:  # Freiflug
                self.special_val['r3'] = 0
                self.version("player_cards")
                self.version("special_val")

        if self.player_role[movep['moveplayer']] == 6:  # Sanitäter
            for disease in range(0, 4):
                if self.healing[disease] == 1:  # disease is healed
                    check_city = [movep['moveto']]
                    if "path" in movep:
                        for c in movep['path']:
                            if c not in check_city:
                                check_city.append(c)
                    for c in check_city:
                        self.infection[disease] += self.city[c]['i'][disease]
                        self.version("infection")
                        self.city[c]['i'][disease] = 0
                        self.version("city", c)
                    if self.infection[disease] > 23:
                        self.healing[disease] = 2  # extinct
                        self.version("healing")

        return self.get_update()

    def endturn(self):
        self.turnsleft(-self.current_player[1])
        return self.get_update()

    def set_next_player(self):

        playernum = self.request.get("value").get('player_num')

        n = 0
        while n < len(self.player_name):
            if self.player_name[n] != "":
                n = n + 1
            else:
                break
        self.current_player = ((playernum + 1) % n, 4)
        self.version("current_player")

        return self.get_update()

    def krisenmanager(self):
        val = self.request.get("value")
        if val['turn'] == "request":
            # no update
            cards = []
            for c in self.carddisposal_player:
                if c > 47:
                    cards.append(c)
            content = {"R": "new_cards",
                       "role3": cards
                       }
            return content
        elif val['turn'] == "getcard":
            self.carddisposal_player.remove(val['card'])
            self.special_val['r3'] = val['card']
            self.turnsleft(-1)
            self.version("special_val")
            return self.get_update()

    def manage_actioncard(self):
        val = self.request.get("value")

        if val['ac'] == 48:  # Prognose
            if val['turn'] == "request":
                if len(self.cardpile_infection) > 5:
                    firstsix = []
                    for c in range(0, 6):
                        firstsix.append(self.cardpile_infection[0])
                        del self.cardpile_infection[0]
                else:
                    firstsix = self.cardpile_infection
                    self.cardpile_infection = []

                # no update
                content = {"R": "new_cards",
                           "action48": firstsix
                           }
                return content
            elif val['turn'] == "exec":
                self.cardpile_infection = val['cards'] + self.cardpile_infection
                if 48 in self.player_cards[val['player']]:
                    self.player_cards[val['player']].remove(48)
                    self.version("player_cards")
                    self.carddisposal_player.append(48)
                else:
                    self.special_val['r3'] = 0
                    self.version("player_cards")
                    self.version("special_val")
                print(self.player_cards[val['player']])
                return self.get_version()
            else:  # cancel
                self.cardpile_infection = val['cards'] + self.cardpile_infection
                return self.get_version()
        if val['ac'] == 50:
            if val['turn'] == "request":
                # no update
                content = {"R": "new_cards",
                           "action50": self.carddisposal_infection
                           }
                return content
            else:  # exec
                self.carddisposal_infection.remove(val['city'])
                self.special_val['a50'].append(val['city'])
                self.version("special_val")
                if 50 in self.player_cards[val['player']]:
                    self.player_cards[val['player']].remove(50)
                    self.version("player_cards")
                    self.carddisposal_player.append(50)
                else:
                    self.special_val['r3'] = 0
                    self.version("player_cards")
                    self.version("special_val")
                return self.get_version()
        if val['ac'] == 51:
            self.city[val['city']]['c'] = 1
            self.version("city", val['city'])
            if val['center_removed'] is not None:
                self.city[val['center_removed']]['c'] = 0
                self.version("city", val['center_removed'])
            if 51 in self.player_cards[val['player']]:
                self.player_cards[val['player']].remove(51)
                self.version("player_cards")
                self.carddisposal_player.append(51)
            else:
                self.special_val['r3'] = 0
                self.version("player_cards")
                self.version("special_val")
            return self.get_version()
        if val['ac'] == 52:
            if 52 in self.player_cards[val['player']]:
                self.player_cards[val['player']].remove(52)
                self.version("player_cards")
                self.carddisposal_player.append(52)
            else:
                self.special_val['r3'] = 0
                self.version("player_cards")
                self.version("special_val")
            self.skipinfection = True
            return self.get_version()

    def deal_cards_player(self):

        if len(self.cardpile_player) > 1:       # check pile
            new_card = self.cardpile_player[0], self.cardpile_player[1]  # draw card
            del self.cardpile_player[0]         # remove card from pile
            del self.cardpile_player[0]         # remove card from pile
            self.version("supply")
            content = {"R": "new_cards",
                       "new_cards": new_card
                       }
            return content
        else:  # last card is drawn -> YOU LOSE -----------------------------------------------
            self.game_STATE = "LOSE_GAME"
            self.reason = "Keine Versorgung mehr möglich."
            self.version("STATE")
            return self.get_update()

    def deal_card_exchange(self):

        val = self.request.get("value")['exchange']

        if val['status'] == "request":
            # if status = request:
            # update CE, everything else is handled by client
            self.card_exchange = val

        if val['status'] == "execute":
            # reset request
            # self.card_exchange = {'status': "", 's': 9, 'c': 99, 'r': 9, 'b': 99, 'd': 0}
            self.card_exchange['status'] = "done"
            if val['d'] != 1:  # execute only when decline = 0
                # remove card from sender
                self.player_cards[val['s']].remove(val['c'])
                # remove burn card from receiver
                if val['b'] in self.player_cards[val['r']]:
                    self.player_cards[val['r']].remove(val['b'])
                # add card to receiver
                self.player_cards[val['r']].append(val['c'])

                self.version("player_cards")
                self.turnsleft(-1)

        self.version("card_exchange")

        return self.get_update()

    def deal_card_infection(self):
        new_card = []
        if not self.skipinfection:
            num = self.newinfection[self.inflvl] if self.inflvl < 6 else 4

            for c in range(0, num):
                new_card.append(self.cardpile_infection[0])
                del self.cardpile_infection[0]
        else:
            self.skipinfection = False

        content = {"R": "new_cards",
                   "new_inf": new_card
                   }

        return content

    def deal_card_epidemie(self):
        # increase infection lvl
        self.inflvl += 1
        self.version("inflvl")

        # draw lowest card
        new_card = [self.cardpile_infection[len(self.cardpile_infection) - 1]]
        self.carddisposal_infection.append(self.cardpile_infection[len(self.cardpile_infection) - 1])
        del self.cardpile_infection[len(self.cardpile_infection) - 1]

        content = {"R": "new_cards",
                   "new_epi": new_card
                   }
        return content

    def update_cards(self):

        update = self.request.get("value")

        for c in update.get('remove'):
            self.player_cards[update.get('player')].remove(c)
            self.carddisposal_player.append(c)

        for c in update.get('add'):
            self.player_cards[update.get('player')].append(c)

        for c in update.get('switch'):
            for i, pc in enumerate(self.player_cards[update.get('player')]):
                if pc == c[0]:
                    self.carddisposal_player.append(pc)
                    self.player_cards[update.get('player')][i] = c[1]

        for c in update.get('burn'):
            self.carddisposal_player.append(c)

        self.version("player_cards")

        return self.get_version()

    def healdisease(self):
        value = self.request.get("value")
        disease = self.city[value.get('cards')[0]].get('d')

        self.healing[disease] = 1
        self.turnsleft(-1)
        self.version("healing")

        if 0 not in self.healing:
            self.game_STATE = "WIN_GAME"
            self.version("STATE")

        for c in value.get('cards'):
            self.player_cards[value.get('player')].remove(c)
            self.carddisposal_player.append(c)

        self.version("player_cards")
        return self.get_version()

    def update_infection(self):

        def check_specialist(pos):
            if 2 in self.player_role:
                specialist = self.player_role.index(2)
                nearby = [pos]
                for con in self.city[pos].get('con'):
                    nearby.append(con)

                if self.player_pos[specialist] in nearby:
                    return True

            return False

        def check_sani(pos, color):
            if 6 in self.player_role:
                if self.player_pos[self.player_role.index(6)] == pos and self.healing[color] == 1:
                    return True
            return False

        value = self.request.get("value")

        # ------ new infection --------------------------------------------------------------------------------------- #
        if "card" in value:
            card = value.get("card")
            disease = self.city[card]['d']

            epidemie = 1 if 'epidemie' in value else 0

            # if epidemie shuffle infection cards
            if epidemie:
                # increase intensity
                random.shuffle(self.carddisposal_infection)

                for c in self.cardpile_infection:
                    self.carddisposal_infection.append(c)
                self.cardpile_infection = self.carddisposal_infection
                self.carddisposal_infection = []
            else:
                self.carddisposal_infection.append(card)

            if self.healing[disease] != 2:  # check if extinct

                if not check_specialist(card) and not check_sani(card, disease):
                    infected = []
                    inf = [card]
                    # when epidemie = 1 add 3 otherwise add 1
                    while len(inf) > 0:
                        if inf[0] not in infected:
                            if self.city[inf[0]]['i'][disease] < 3 - (2 * epidemie):
                                self.city[inf[0]]['i'][disease] += (1 + 2 * epidemie)
                                self.version("city", inf[0])
                                if self.infection[disease] > 0 + (2 * epidemie):
                                    self.infection[disease] -= (1 + 2 * epidemie)
                                    self.version("infection")
                                else:
                                    # -> YOU LOSE -----------------------------------------------
                                    self.game_STATE = "LOSE_GAME"
                                    switcher = {
                                        0: "Blaue Seuche außer Kontrolle",
                                        1: "Gelbe Seuche außer Kontrolle",
                                        2: "Grüne Seuche außer Kontrolle",
                                        3: "Rote Seuche außer Kontrolle"
                                    }
                                    self.reason = switcher.get(disease)
                                    self.version("STATE")
                            else:  # outbreak
                                self.outbreak += 1
                                self.version("outbreak")
                                if self.outbreak >= 8:
                                    # -> YOU LOSE -----------------------------------------------
                                    self.game_STATE = "LOSE_GAME"
                                    self.reason = "Zu viele Ausbrüche"
                                    self.version("STATE")
                                for o in self.city[inf[0]].get("con"):
                                    if o not in infected \
                                            and o not in inf \
                                            and not check_specialist(o) \
                                            and not check_sani(o, disease):
                                        inf.append(o)

                            infected.append(inf[0])
                            epidemie = 0  # use epidemie only in first round
                        del inf[0]
        # ------ remove infection ------------------------------------------------------------------------------------ #
        else:
            player = value.get('player')
            disease = value.get('disease')

            if self.city[self.player_pos[player]]['i'][disease] > 0:
                if self.player_role[player] == 6:  # sanitäter
                    self.infection[disease] += self.city[self.player_pos[player]]['i'][disease]
                    self.city[self.player_pos[player]]['i'][disease] = 0
                else:  # other player
                    self.infection[disease] += 1
                    self.city[self.player_pos[player]]['i'][disease] -= 1
                    # after healing remove infection from sanitäter
                    for p, num in enumerate(self.player_role):
                        if p == 6:
                            self.infection[disease] += self.city[self.player_pos[num]]['i'][disease]
                            self.city[self.player_pos[num]]['i'][disease] = 0
                            break
                self.version("city", self.player_pos[player])
                self.version("infection")

                self.turnsleft(-1)

                if self.infection[disease] > 23 and self.healing[disease] > 0:
                    self.healing[disease] = 2  # extinct
                    self.version("healing")
                    if 0 not in self.healing:
                        self.game_STATE = "WIN_GAME"
                        self.version("STATE")

        return self.get_update()

    def update_center(self):

        update = self.request.get("value")
        # 'player': self.this_player_num,
        # 'center_new': pos,
        # 'center_removed': None,
        # 'usedcards': []}
        self.city[update.get('center_new')]['c'] = 1
        self.version("city", update.get('center_new'))
        if update.get('center_removed') is not None:
            self.city[update.get('center_removed')]['c'] = 0
            self.version("city", update.get('center_removed'))
        if self.player_role[update.get('player')] != 7:
            self.player_cards[update.get('player')].remove(update.get('center_new'))
            self.version("player_cards")

        self.turnsleft(-1)

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
                        except Exception as e:
                            print(
                                "main: error: exception for",
                                f"{message.addr}:\n{traceback.format_exc()}",
                                e
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

        self.errormsg = ""

        tk.Tk.__init__(self)

        self.title("Pandemie | Server")
        self.geometry("150x400+600+1")

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
        self.btn_startgame.pack(fill=X, pady=(10, 5), padx=10)

        self.btn_helper = Button(self, text='helper', command=self.btn_helper)
        self.btn_helper.pack(fill=X, pady=5, padx=10)

        seph = ttk.Separator(self, orient=HORIZONTAL)
        seph.pack(fill=X, pady=10, padx=5)

        self.lblerror = Label(self, text="State", font="Helvetica 10", anchor='w')
        self.lblerror.pack(fill=X, pady=0, padx=5)
        self.lblerrormsg = Label(self, text="-", font="Helvetica 10", anchor='w')
        self.lblerrormsg.pack(fill=X, pady=0, padx=10)

        self.myserver = Server()
        self.myserver.start()

        self.helper = GameStats
        self.gui_loop()

    def btn_helper(self):
        self.helper = GameStats(self.myserver)

    def btn_startgame(self):
        self.btn_startgame.configure(text="game running", state=DISABLED)
        self.myserver.startgame(self.v.get())

    def gui_loop(self):
        self.lblstatus.configure(text=self.myserver.external_ip)

        self.player = self.myserver.player_name
        self.player_rdy = self.myserver.player_rdy

        self.errormsg = self.myserver.error_message

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
            self.lbl_plr_3.configure(text=self.player[3])
        if self.player_rdy[3]:
            self.lbl_plr_3.configure(bg="SeaGreen1")

        if self.errormsg != "":
            self.lblerrormsg.configure(fg="#990000", font='Helvetica 10 bold', text=self.errormsg)
        else:
            self.lblerrormsg.configure(fg="#000000", font='Helvetica 10', text="no error")
        self.after(1000, self.gui_loop)


class GameStats(tk.Tk):
    def __init__(self, args):
        self.server = args
        self.card_epidemie = 53
        tk.Tk.__init__(self)
        self.title("Pandemie | Helper")
        self.geometry("590x1100+1+1")

        self.lbl_stat_1 = Label(self, text="Status", font=("Helvetica", 10, 'bold'), justify=LEFT)
        self.lbl_stat_2 = Label(self, text="", font="Helvetica 10", justify=LEFT)
        sep1 = ttk.Separator(self, orient=HORIZONTAL)
        self.lbl_p1 = Label(self, text="", font=("Helvetica", 10, 'bold'), justify=LEFT)
        self.lbl_p2 = Label(self, text="", font=("Helvetica", 10, 'bold'), justify=LEFT)
        self.lbl_p3 = Label(self, text="", font=("Helvetica", 10, 'bold'), justify=LEFT)
        self.lbl_p4 = Label(self, text="", font=("Helvetica", 10, 'bold'), justify=LEFT)
        self.lbl_player = [self.lbl_p1,  self.lbl_p2,  self.lbl_p3, self.lbl_p4]
        sepv1 = ttk.Separator(self, orient=VERTICAL)
        sepv2 = ttk.Separator(self, orient=VERTICAL)
        sepv3 = ttk.Separator(self, orient=VERTICAL)
        sepvp = [sepv1, sepv2, sepv3]
        self.lbl_p1c = Label(self, text="", font="Helvetica 10", justify=LEFT)
        self.lbl_p2c = Label(self, text="", font="Helvetica 10", justify=LEFT)
        self.lbl_p3c = Label(self, text="", font="Helvetica 10", justify=LEFT)
        self.lbl_p4c = Label(self, text="", font="Helvetica 10", justify=LEFT)
        self.lbl_player_cards = [self.lbl_p1c, self.lbl_p2c, self.lbl_p3c, self.lbl_p4c]
        sep2 = ttk.Separator(self, orient=HORIZONTAL)
        self.lbl_card1 = Label(self, text="", font="Helvetica 10", justify=LEFT)
        self.lbl_card2 = Label(self, text="", font="Helvetica 10", justify=LEFT)
        sepv4 = ttk.Separator(self, orient=VERTICAL)
        self.lbl_card3 = Label(self, text="", font="Helvetica 10", justify=LEFT)
        self.lbl_card4 = Label(self, text="", font="Helvetica 10", justify=LEFT)

        self.lbl_stat_1.grid(row=1, column=1, padx=0, pady=0, columnspan=7, sticky=W)
        self.lbl_stat_2.grid(row=2, column=1, padx=0, pady=0, columnspan=7, sticky=W)
        sep1.grid(row=3, pady=5, columnspan=8, sticky="ew")

        for c, p in enumerate(self.lbl_player):
            p.grid(row=4, column=(c + 1)*2-1, padx=0, pady=0, sticky=W)
        for c, p in enumerate(self.lbl_player_cards):
            p.grid(row=5, column=(c + 1)*2-1, padx=0, pady=0, sticky=N)
        for c, s in enumerate(sepvp):
            s.grid(row=4, column=(c+1)*2, rowspan=2, padx=5, sticky="ns")

        sep2.grid(row=6, pady=5, columnspan=8, sticky="ew")
        self.lbl_card1.grid(row=7, column=1, padx=0, pady=0, sticky=NW)
        self.lbl_card2.grid(row=7, column=3, padx=0, pady=0, sticky=NW)
        sepv4.grid(row=7, column=4, padx=5, sticky="ns")
        self.lbl_card3.grid(row=7, column=5, padx=0, pady=0, sticky=NW)
        self.lbl_card4.grid(row=7, column=7, padx=0, pady=0, sticky=NW)

        self.helper_loop()

    def helper_loop(self):
        serverversion = self.server.server_version
        state = self.server.game_STATE              # "INIT"
        player_name = self.server.player_name       # ["", "", "", ""]
        player_role = self.server.player_role       # [0, 0, 0, 0]
        player_cards = self.server.player_cards     # [[], [], [], []]  # in data2send included
        player_pos = self.server.player_pos         # [2, 2, 2, 2]
        cur = self.server.current_player            # 0

        stat_infection = self.server.infection      # [24, 24, 24, 24]
        stat_outbreak = self.server.outbreak        # 0
        stat_inflvl = self.server.inflvl            # 0
        stat_healing = self.server.healing          # [0, 1, 0, 2]  # 0 = active,  1 = healed,  2 = exterminated

        stat_exchange = self.server.card_exchange
        stat_role3 = self.server.special_val

        cardpile_player = self.server.cardpile_player                   # []
        cardpile_infection = self.server.cardpile_infection             # []
        carddisposal_player = self.server.carddisposal_player           # []
        carddisposal_infection = self.server.carddisposal_infection     # []
        city = self.server.city

        self.lbl_stat_1.configure(text=("STATE: " + state + ", v: " + str(serverversion) + ", Current: " + str(cur)))
        self.lbl_stat_2.configure(text=("Infektion: " + str(stat_infection) +
                                        ", Outbreak: " + str(stat_outbreak) +
                                        ", inflvl: " + str(stat_inflvl) +
                                        ", Healing: " + str(stat_healing)) +
                                        "\n EXCHANGE: " + str(stat_exchange) +
                                        ", special_val " + str(stat_role3))
        for c, p in enumerate(self.lbl_player):
            p.configure(text=("Player " + str(c) + "\n" + player_name[c] +
                              "\n role: " + str(player_role[c]) +
                              "\n pos: " + str(player_pos[c])))

        for c, p in enumerate(self.lbl_player_cards):
            line = "Player " + str(c) + " Cards:\n"
            for i in player_cards[c]:
                # line += str(i) + "\n"
                if i < 48:
                    line += city[i].get("name") + " (" + str(i) + ")\n"
                else:
                    line += str(i) + "\n"
            p.configure(text=line)

        cardpile = "Player Cards:\n\n"
        for c in cardpile_player:
            if c < 48:
                cardpile += city[c].get("name") + " (" + str(c) + ")\n"
            elif c == self.card_epidemie:
                cardpile += "<< EPIDEMIE >>" + "\n"
            else:
                cardpile += str(c) + "\n"
        self.lbl_card1.configure(text=cardpile)

        cardpile = "Player Disposal:\n\n"
        for c in carddisposal_player:
            if c < 48:
                cardpile += city[c].get("name") + " (" + str(c) + ")\n"
            elif c == self.card_epidemie:
                cardpile += "<< EPIDEMIE >>" + "\n"
            else:
                cardpile += str(c) + "\n"
        self.lbl_card2.configure(text=cardpile)

        cardpile = "Infection Cards:\n\n"
        for c in cardpile_infection:
            if c < 48:
                cardpile += city[c].get("name") + " (" + str(c) + ")\n"
            elif c == self.card_epidemie:
                cardpile += "<< EPIDEMIE >>" + "\n"
            else:
                cardpile += str(c) + "\n"
        self.lbl_card3.configure(text=cardpile)

        cardpile = "Infection Disposal:\n\n"
        for c in carddisposal_infection:
            if c < 48:
                cardpile += city[c].get("name") + " (" + str(c) + ")\n"
            elif c == self.card_epidemie:
                cardpile += "<< EPIDEMIE >>" + "\n"
            else:
                cardpile += str(c) + "\n"
        self.lbl_card4.configure(text=cardpile)

        self.after(1000, self.helper_loop)


if __name__ == '__main__':
    app = ServerInterface()  # start UI -> ui starts server
    app.mainloop()

    # app.helper.destroy()

    # TODO close sub classes (myserver)
