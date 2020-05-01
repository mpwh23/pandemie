
# game
    def game_engine(self, m_response):

        # region MANAGE state ##########################################################################################


        if self.game_STATE == "ACTION":
            if self.this_player_turns["turns_left"] > 1:
                self.txt_status = "Aktionsphase: " + str(
                    self.this_player_turns["turns_left"]) + " Aktionen verbleibend."
            elif self.this_player_turns["turns_left"] == 1:
                self.txt_status = "Aktionsphase: Eine Aktion verbleibend."
            else:  # turn is over -> draw cards
                self.this_player_turns["turn"] = 0
                self.txt_action = ""
                self.value = self.this_player_num
                self._update('draw_playercard')

        if self.game_STATE == "SUPPLY":
            if len(self.this_player_drawcards) > 0:
                if self.this_player_drawcards[0] != self.card_epidemie:
                    if len(self.this_player_drawcards) > 1:
                        self.txt_status = "Nachschubphase: 2 Karten ziehen"
                    else:
                        self.txt_status = "Nachschubphase: 1 Karten ziehen"
                else:
                    if self.this_player_turns["turn"] == 201:
                        self.txt_status = "Epidemie auslösen"
            else:  # supply over go to infect
                self.game_canvas.itemconfigure(self.i_quicktip, fill="")
                self.this_player_turns["turn"] = 0
                self.txt_action = ""
                self.value = self.this_player_num
                self._update('draw_infcard')

        if self.game_STATE == "EPIDEMIE" and len(self.this_player_drawcards) != 0:
            # self.this_player_turns["turn"] = 666
            print("www")
            # self.value = self.this_player_num
            # self.action = 'getVersion'
            # self._update()

        if self.game_STATE == "INFECT" and len(self.this_player_drawcards) == 0:
            self.this_player_turns["turn"] = 0
            self.txt_action = ""
            self.txt_status = ""
            print(self.value)
            print("next player")
            self.game_STATE = "PASSIV"
            self.value = self.this_player_num
            self._update('turn_over')

        # endregion

    def game_click(self, event):
        # print(event)
        # print(str(self.section_status) + " > " + str(event.y) + " > " + str(self.section_action + 8))

        # region ###### functions ######################################################################################
        def turn_10_move(sender, *args):
            if sender == "BTN":  # initialize action
                self.this_player_turns['turn'] = 10
                self.get_player_path()
                self.draw_city_highlight(self.this_player_range)
                self.txt_action = "Bewegen: Wähle Ziel. (keine Karte notwendig)"
            else:  # do action
                self.draw_city_highlight([])
                if args[0] != self.all_player_pos[self.this_player_num] and \
                        args[1] <= self.this_player_turns['turns_left']:
                    self.this_player_turns['turns_left'] -= args[1]
                    # update server
                    self.value = {'player': self.this_player_num,
                                  'moveto': args[0],
                                  'usedcards': []}
                    self.action = 'player_move'
                    return ""
                else:
                    return "Zug ungültig - Nicht genug Aktionen"

        def turn_11_fly_direct(sender, *args):
            if sender == "BTN":  # initialize action
                self.this_player_turns['turn'] = 11
                self.draw_city_highlight(self.this_player_cards)
                self.txt_action = "Direktflug: Wähle Ziel. (eine Karte wird benötigt)"
            else:  # do action
                self.draw_city_highlight([])
                if args[0] in self.this_player_cards:
                    self.this_player_turns['turns_left'] -= 1
                    # update server
                    self.value = {'player': self.this_player_num,
                                  'moveto': args[0],
                                  'usedcards': [args[0]]}
                    self.action = 'player_move'
                    return ""
                else:
                    return "Zug ungültig - Stadtkarte nicht vorhanden"

        def turn_12_fly_charter(sender, *args):
            if sender == "BTN":  # initialize action
                if self.all_player_pos[self.this_player_num] in self.this_player_cards:
                    self.this_player_turns['turn'] = 12
                    self.txt_action = "Charterflug: Wähle Zielstadt."
                    allcitys = [x for x in range(48)]
                    allcitys.remove(self.all_player_pos[self.this_player_num])
                    self.draw_city_highlight(allcitys)
                else:
                    self.txt_action = "Charterflug nicht möglich. (Karte vom Standort wird benötigt)"
            else:  # do action
                self.draw_city_highlight([])
                if self.all_player_pos[self.this_player_num] in self.this_player_cards:
                    self.this_player_turns['turns_left'] -= 1
                    # update server
                    self.value = {'player': self.this_player_num,
                                  'moveto': args[0],
                                  'usedcards': [args[0]]}
                    self.action = 'player_move'
                    return ""
                else:
                    return "Zug ungültig - Stadtkarte nicht vorhanden"

        def turn_13_fly_special(sender, *args):
            if sender == "BTN":  # initialize action
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
            else:  # do action
                self.draw_city_highlight([])
                if self.city[self.all_player_pos[self.this_player_num]]['center'] and \
                        self.city[args[0]]['center']:
                    self.this_player_turns['turns_left'] -= 1
                    # update server
                    self.value = {'player': self.this_player_num,
                                  'moveto': args[0],
                                  'usedcards': []}
                    self.action = 'player_move'
                    return ""
                else:
                    return "Zug ungültig - kein Forschungscenter"

        def btn_32_end_turn(*args):
            self.this_player_turns = {'turns_left': 0, 'turn': 0, 'target': 0, 'use': 0}
            self.txt_action = ""

        def btn_33_game_reload(*args):
            self.txt_action = "reload Game..."
            self.localversion = 0

        def turn_101_draw_playercard(card):
            # TODO calculation on server???
            add_playercard = []
            remove_playercard = []
            switch = []
            burncard = []
            if 7 > card >= len(self.this_player_cards):  # add card to player
                add_playercard.append(self.this_player_drawcards[0])
            elif card == 7:  # dismiss card
                burncard.append(self.this_player_drawcards[0])
            else:  # replace card
                switch.append((self.this_player_cards[card], self.this_player_drawcards[0]))

            del self.this_player_drawcards[0]
            self.receive_card()  # update drawcards
            # update server
            self.value = {'player': self.this_player_num,
                          'add': add_playercard,
                          'remove': remove_playercard,
                          'switch': switch,
                          'burn': burncard}
            self.action = 'update_cards'

        def turn_201_epidemie_inf(card):
            if card == 7:  # click on epidemie Card
                self.game_canvas.itemconfigure(self.i_quicktip, fill="")
                self.this_player_turns["turn"] = 0
                self.txt_action = ""
                self.value = self.this_player_num
                self._update('draw_epidemiecard')

        def turn_301_infection(card):
            if card == 7:  # click on infection-card only
                _print()
                # update local
                inf_card = self.this_player_drawcards[0]
                del self.this_player_drawcards[0]
                self.receive_card()  # update drawcards

                # update server -> do calculation online
                self.value = {'card': inf_card}
                self.action = 'update_inf'

# todo
        def card_cure(c_num):
            if c_num in self.this_player_card_selection:
                self.this_player_card_selection.remove(c_num)
                self.draw_card_highlight([c_num], "#ff0000")
            else:
                self.this_player_card_selection.append(c_num)
                self.draw_card_highlight([c_num], "#00ff00")

            if len(self.this_player_card_selection) < 5 and not self.all_player_role[self.this_player_num] == 1:
                return str(len(self.this_player_card_selection)) + "/5 Karten ausgewählt"
            elif len(self.this_player_card_selection) == 5 and not self.all_player_role[self.this_player_num] == 1:
                self.this_player_turns['turn'] = 62
                return "Heilmittel entdecken."

            if len(self.this_player_card_selection) < 4 and self.all_player_role[self.this_player_num] == 1:
                return str(len(self.this_player_card_selection)) + "/4 Karten ausgewählt"
            elif len(self.this_player_card_selection) == 4 and not self.all_player_role[self.this_player_num] == 1:
                self.this_player_turns['turn'] = 62
                return "Heilmittel entdecken."

            # TODO delete cardselection

        def btn_03_build_center():
            # init var
            pos = self.all_player_pos[self.this_player_num]

            center = []
            for anz, c in enumerate(self.city):
                if c.get("center"):
                    center.append(anz)

            if pos in self.this_player_cards or \
                    self.all_player_role[self.this_player_num] == 7:  # betriebsexperte

                if len(center) < 6:  # build new center
                    if self.city[pos]['center'] != 1:
                        # update local
                        self.city[pos]['center'] = 1
                        self.this_player_turns['turns_left'] -= 1

                        if self.all_player_role[self.this_player_num] != 7:
                            self.this_player_cards.remove(pos)

                        # update game
                        self.game_show({'city': [pos], 'cards': 1})

                        # update server
                        self.value = {'player': self.this_player_num,
                                      'center_new': pos,
                                      'center_removed': None,
                                      'cards': self.this_player_cards}
                        self.action = 'center'

                    else:
                        self.txt_action = "Nur ein Forschungscenter möglich."
                else:  # move existing center
                    self.draw_city_highlight(center)
                    self.txt_action = "Wähle Center zum verschieben"
                    # todo forschungscenter max = 6
            else:
                self.txt_action = "Stadtkarte benötigt"

        def btn_04_cure():
            pass

        def btn_05_share():
            pass

        def btn_06_discover():
            check = [0, 0, 0, 0]
            for c in self.this_player_cards:
                if c <= 47:
                    check[self.city[c].get("farbe")] += 1
            for idf, f in enumerate(check):
                if f > 4 \
                        or (self.all_player_role[self.this_player_num] == 1 and f > 3):  # exeption Wissenschaftler
                    selection = []
                    for idc, c in enumerate(self.this_player_cards):
                        if self.city[c].get("farbe") == idf:
                            selection.append(idc)

                    self.this_player_turns['turn'] = 6
                    self.this_player_turns['target'] = idf
                    if self.all_player_role[self.this_player_num] == 1:
                        self.txt_action = "Wähle 4 Karten aus."
                    else:
                        self.txt_action = "Wähle 5 Karten aus."
                    self.draw_card_highlight(selection, "#ff0000")
                    break
                else:
                    self.txt_action = "Nicht genug Karten von einer Farbe"

        def btn_06_dodiscover():
            # self.this_player_card_selection
            pass
        # endregion

        if not self.block_request:
            # region ###### CLICK @ CARDS ##############################################################################
            if 8 < event.y < self.section_card:  # cardsection
                card_num = math.floor(float(event.x) / (self.section_game_w / 8))
                print("clicked at Card: " + str(card_num))

                switcher = {
                    6: card_cure,  # cure
                    101: turn_101_draw_playercard,  # draw_card
                    201: turn_201_epidemie_inf,
                    301: turn_301_infection,
                }
                func = switcher.get(self.this_player_turns['turn'], lambda m: "Zug ungültig")

                if len(self.this_player_drawcards) > 0 or 0 < self.this_player_turns['turn'] < 100:
                    self.txt_action = func(card_num)  # execute
            # endregion
            # region ###### CLICK @ FIELD ##############################################################################
            elif self.section_field > event.y > self.section_card + 8:  # map -> find city
                # find city
                dist = 32000
                mycity = ""
                mycitynum = 0
                fy = (event.y - (self.section_card + 8))  # y-pos on field
                for c in self.city:
                    if (0 + abs(c.get("posX") * self.section_game_w / 100 - event.x) +
                            abs(c.get("posY") * self.section_game_w / 100 / 2.125 - fy)) < dist:
                        dist = (abs(c.get("posX") * self.section_game_w / 100 - event.x) +
                                abs(c.get("posY") * self.section_game_w / 100 / 2.125 - fy))
                        mycity = c.get("name")
                        mycitynum = c.get("ID")
                if dist < (self.section_game_w / 100 * 3):
                    # print("clicked at City: " + mycity)
                    steps = len(self.get_player_path(mycitynum))

                    switcher = {
                        10: turn_10_move,
                        11: turn_11_fly_direct,
                        12: turn_12_fly_charter,
                        13: turn_13_fly_special,
                    }
                    func = switcher.get(self.this_player_turns['turn'], lambda sender, n, step: "Zug ungültig")

                    if self.this_player_turns['turns_left'] > 0:
                        self.txt_action = func("CITY", mycitynum, steps)  # execute
                    else:
                        self.txt_action = "keine Züge vorhanden"
            # endregion
            # region ###### CLICK @ BAR/BTN ############################################################################
            elif event.y > self.section_field + 8:
                posx = self.game_canvas.coords(tk.CURRENT)[0] + event.widget.winfo_width() / 68
                num = math.floor(float(posx) / self.section_game_w * 34)

                _print("action-BTN", str(num), "clicked.")
                switcher = {
                    3: btn_03_build_center,
                    4: btn_04_cure,
                    5: btn_05_share,
                    6: btn_06_discover,
                    62: btn_06_dodiscover,
                    10: turn_10_move,
                    11: turn_11_fly_direct,
                    12: turn_12_fly_charter,
                    13: turn_13_fly_special,
                    # 17: btn_17_turn_execute,
                    32: btn_32_end_turn,
                    33: btn_33_game_reload
                    # TODO aktionen
                }
                func = switcher.get(num, lambda sender: None)

                if self.this_player_turns['turns_left'] > 0 and self.game_STATE == "ACTION":
                    func("BTN")  # execute
                else:
                    if self.this_player_turns['turns_left'] <= 0:
                        self.txt_action = "keine Züge vorhanden"
                    else:
                        self.txt_action = "Du bist nicht am Zug."

            # endregion

            self.i_action.configure(text=self.txt_action)  # update description for player
            self.i_status.configure(text=self.txt_status)  # update description for player

            self._update()


# main game

    def receive_card(self, *args):
        _print(args)

        # get args from response
        if len(args) > 0:
            if 'new_cards' in args[0] and self.game_STATE == "ACTION":
                self.this_player_drawcards = args[0]['new_cards']
                self.txt_status = "Nachschubphase"
                self.game_STATE = "SUPPLY"
            if 'new_inf' in args[0] and self.game_STATE == "SUPPLY":
                self.this_player_drawcards = args[0]['new_inf']
                self.txt_status = "Infektionsphase"
                self.game_STATE = "INFECT"

            if 'new_epi' in args[0] and self.game_STATE == "SUPPLY":
                old = self.this_player_drawcards
                self.this_player_drawcards = [args[0]['new_epi'][0]]
                for o in old:
                    self.this_player_drawcards.append(o)
                self.game_STATE = "EPIDEMIE"

        print("<<< " + str(self.this_player_drawcards) + " >>>")
        # update local game
        self.draw_cards()
        self.draw_card_highlight()
        _print(self.this_player_drawcards)

        # set next turn
        if len(self.this_player_drawcards) > 0:
            if self.this_player_drawcards[0] != self.card_epidemie:
                if self.game_STATE == "SUPPLY":
                    self.this_player_turns['turn'] = 101
                    self.txt_action = "Ziehe Karte."
                if self.game_STATE == "INFECT":
                    self.this_player_turns['turn'] = 301
                    self.txt_action = "Infiziere Stadt"
            else:
                # epidemie
                if self.game_STATE == "SUPPLY":
                    self.this_player_turns['turn'] = 201
                    self.txt_action = "Epidemie."
                if self.game_STATE == "EPIDEMIE":
                    self.this_player_turns['turn'] = 202
                    self.txt_action = "Infiziere Stadt 2"

        self.i_action.configure(text=self.txt_action)  # update description for player
        self.i_status.configure(text=self.txt_status)  # update description for player

        return 'getVersion'

    def next_player(self, args):
        _print(args)
        # "response": "next_player",
        # "v": self.serverversion,
        # "cur_player": self.current_player,
        self.this_player_turns = {'turns_left': 0, 'turn': 0, 'target': 0, 'use': 0}
        self.current_player = args.get("cur_player")
        self.localversion = args.get("v")

        return 'getVersion'

















########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################




def update_server_window():
    if self.player_name[0] != "":
        self.lbl_plr_0.configure(text=self.player_name[0])
    if self.player_rdy[0]:
        self.lbl_plr_0.configure(bg="SeaGreen1")

    if self.player_name[1] != "":
        self.lbl_plr_1.configure(text=self.player_name[1])
    if self.player_rdy[1]:
        self.lbl_plr_1.configure(bg="SeaGreen1")

    if self.player_name[2] != "":
        self.lbl_plr_2.configure(text=self.player_name[2])
    if self.player_rdy[2]:
        self.lbl_plr_2.configure(bg="SeaGreen1")

    if self.player_name[3] != "":
        self.lbl_plr_2.configure(text=self.player_name[3])
    if self.player_rdy[3]:
        self.lbl_plr_2.configure(bg="SeaGreen1")

### old MainGame

class MainGame(tk.Tk):
    def __init__(self):
        self.host = client_host
        self.value = get_player()

        self.num = thisplayer
        self.player_role = player_role

        tk.Tk.__init__(self)

        # region rescources

        # endregion

        self.title("Pandemie")  # region UI

        user32 = ctypes.windll.user32
        screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        print(str(user32.GetSystemMetrics(0)) + "x" + str(user32.GetSystemMetrics(1)))
        self.geometry(str(user32.GetSystemMetrics(0) - 100) + "x" + str(user32.GetSystemMetrics(1) - 100) + "+10+10")

        self.canvas = Canvas(self, borderwidth=1)
        self.frame = Frame(self.canvas)
        self.vsb = Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4, 4), window=self.frame, anchor="nw", tags="self.frame")
        # canvas.create_text(225, 225, font=("Helvetica", 14), text="Item 5", tags="DnD")
        self.img = PhotoImage(file=r"D:\_PROJEKTE\2020\2020_04_pandemie\data\pos_50p_pad100.png")
        self.canvas.create_image(0, 0, anchor=NW, image=self.img)

        self.canvas.create_oval(100 - 16, 261 - 16, 100 + 16, 261 + 16, outline='blue', width=3)  # San Francisco
        self.canvas.create_oval(261 - 16, 214 - 16, 261 + 16, 214 + 16, outline='blue', width=3)  # Chicago


        self.canvas.pack(expand=1, fill=tk.BOTH)

        # endregion


#canvas.create_oval(307-16,307-16,307+16,307+16, outline='blue',width = 3) #Atlanta
#canvas.create_oval(386-16,210-16,386+16,210+16, outline='blue',width = 3) #Montréal
#canvas.create_oval(483-16,225-16,483+16,225+16, outline='blue',width = 3) #New York
#canvas.create_oval(440-16,301-16,440+16,301+16, outline='blue',width = 3) #Washington
#canvas.create_oval(698-16,273-16,698+16,273+16, outline='blue',width = 3) #Madrid
#canvas.create_oval(715-16,149-16,715+16,149+16, outline='blue',width = 3) #London
#canvas.create_oval(811-16,211-16,811+16,211+16, outline='blue',width = 3) #Paris
#canvas.create_oval(842-16,124-16,842+16,124+16, outline='blue',width = 3) #Essen
#canvas.create_oval(894-16,187-16,894+16,187+16, outline='blue',width = 3) #Mailand
#canvas.create_oval(981-16,101-16,981+16,101+16, outline='blue',width = 3) #St. Petersburg
#canvas.create_oval(127-16,386-16,127+16,386+16, outline='yellow',width = 3) #Los Angeles
#canvas.create_oval(243-16,428-16,243+16,428+16, outline='yellow',width = 3) #Mexico Stadt
#canvas.create_oval(387-16,408-16,387+16,408+16, outline='yellow',width = 3) #Miami
#canvas.create_oval(376-16,534-16,376+16,534+16, outline='yellow',width = 3) #Bogotá
#canvas.create_oval(332-16,669-16,332+16,669+16, outline='yellow',width = 3) #Lima
#canvas.create_oval(349-16,810-16,349+16,810+16, outline='yellow',width = 3) #Santiago
#canvas.create_oval(481-16,785-16,481+16,785+16, outline='magenta',width = 3) #Buenos Aires
#canvas.create_oval(554-16,689-16,554+16,689+16, outline='yellow',width = 3) #Sao Paulo
#canvas.create_oval(798-16,511-16,798+16,511+16, outline='yellow',width = 3) #Lagos
#canvas.create_oval(875-16,594-16,875+16,594+16, outline='yellow',width = 3) #Kinshasa
#canvas.create_oval(948-16,724-16,948+16,724+16, outline='yellow',width = 3) #Johannisburg
#canvas.create_oval(959-16,488-16,959+16,488+16, outline='yellow',width = 3) #Khartum
#canvas.create_oval(836-16,342-16,836+16,342+16, outline='green',width = 3) #Algier
#canvas.create_oval(932-16,365-16,932+16,365+16, outline='green',width = 3) #Kairo
#canvas.create_oval(950-16,260-16,950+16,260+16, outline='green',width = 3) #Istanbul
#canvas.create_oval(1048-16,186-16,1048+16,186+16, outline='green',width = 3) #Moskau
#canvas.create_oval(1039-16,324-16,1039+16,324+16, outline='green',width = 3) #Bagdad
#canvas.create_oval(1054-16,439-16,1054+16,439+16, outline='orange',width = 3) #Riad
#canvas.create_oval(1133-16,246-16,1133+16,246+16, outline='green',width = 3) #Teheran
#canvas.create_oval(1160-16,368-16,1160+16,368+16, outline='green',width = 3) #Karatschi
#canvas.create_oval(1170-16,459-16,1170+16,459+16, outline='green',width = 3) #Mumbai
#canvas.create_oval(1251-16,330-16,1251+16,330+16, outline='green',width = 3) #Delhi
#canvas.create_oval(1269-16,524-16,1269+16,524+16, outline='green',width = 3) #Chennai
#canvas.create_oval(1339-16,360-16,1339+16,360+16, outline='green',width = 3) #Kalkutta
#canvas.create_oval(1409-16,215-16,1409+16,215+16, outline='magenta',width = 3) #Peking
#canvas.create_oval(1521-16,210-16,1521+16,210+16, outline='magenta',width = 3) #Seoul
#canvas.create_oval(1418-16,305-16,1418+16,305+16, outline='magenta',width = 3) #Shanghai
#canvas.create_oval(1609-16,260-16,1609+16,260+16, outline='magenta',width = 3) #Tokyo
#canvas.create_oval(1357-16,467-16,1357+16,467+16, outline='magenta',width = 3) #Bangkok
#canvas.create_oval(1430-16,410-16,1430+16,410+16, outline='magenta',width = 3) #Hong Kong
#canvas.create_oval(1530-16,393-16,1530+16,393+16, outline='magenta',width = 3) #Taipeh
#canvas.create_oval(1620-16,354-16,1620+16,354+16, outline='magenta',width = 3) #Osaka
#canvas.create_oval(1356-16,632-16,1356+16,632+16, outline='magenta',width = 3) #Jakarta
#canvas.create_oval(1436-16,555-16,1436+16,555+16, outline='magenta',width = 3) #Ho-Chi-MinH-Stadt
#canvas.create_oval(1558-16,549-16,1558+16,549+16, outline='magenta',width = 3) #Manila
#canvas.create_oval(1628-16,807-16,1628+16,807+16, outline='magenta',width = 3) #Sydney



        self.task_main()

    # region UI elements ###############################################################################################

    # endregion

    # region game engine ###############################################################################################
    # actions
    def update_client(self, args):
        #print("init_update: " + str(args))

        # update version
        set_lv(args.get("v"))

        # player_name
        pn = args.get("player")
        self.lbl11.configure(text=pn[0]+"\n"+pn[1]+"\n"+pn[2]+"\n"+pn[3])

        # player role
        pr = args.get("player_role")
        self.lbl21.configure(text=get_role_name(pr[0]) + "\n" +
                                  get_role_name(pr[1]) + "\n" +
                                  get_role_name(pr[2]) + "\n" +
                                  get_role_name(pr[3]))

        setaction('getVersion')
        return update_intervall

    def gameclient(self, m):
        # print("GameCient: " + str(m))

        if m.get("response"):
            switcher = {
                "update":       self.update_client,
                "player_rdy":   self.update_client,
            }
            # Get the function from switcher dictionary
            func = switcher.get(m.get("response"))
            u = func(m)  # execute
        else:
            u = update_intervall
            print("FAILURE: Game Engine - No response")
        return u
    # endregion

    def task_main(self):
        request = create_request(getaction(), self.value)
        start_connection(self.host, port, request)
        update = update_intervall
        try:
            while True:
                events = sel.select(timeout=1)
                for key, mask in events:
                    message = key.data
                    try:
                        message.process_events(mask)
                        if mask == 1:

                            if message.getVersion() is not None:
                                if message.getVersion() != get_lv():
                                    setaction("get_update")
                                    self.value = get_player()
                                else:
                                    update = update_intervall
                            else:
                                update = self.gameclient(message.get_response())

                    except Exception:
                        print(
                            "main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}",
                        )
                        message.close()
                # Check for a socket being monitored to continue.
                if not sel.get_map():
                    break
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")

        # if getversion -> updatetime = updateinterval else direct
        if getaction() != 'getVersion':
            update = 1
        # print(">> befor wait" + str(message.getVersion()))
        # loop within mainloop
        self.after(update_intervall, self.task_main)




### Client different classes

#!/usr/bin/env python3

import socket
import selectors
import traceback
import tkinter as tk
from tkinter import *
import urllib.request
import ctypes
import time

from PIL import Image, ImageTk

from Pandemie import libclient

########################################################################################################################
update_intervall = 3000
port = 9999
localversion = 0
action = 'getVersion'
thisplayer = 0
res_path = "D:/_PROJEKTE/2020/Python/Pandemie/"
########################################################################################################################

sel = selectors.DefaultSelector()


# region global functions
def getaction():
    global action
    return action


def setaction(newaction):
    global action
    action = newaction


def get_lv():
    global localversion
    return localversion


def set_lv(newversion):
    global localversion
    localversion = newversion


def get_player():
    global thisplayer
    return thisplayer


def set_player(newplayer):
    global thisplayer
    thisplayer = newplayer


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


def get_player_num(all, name):
    ret = 0
    for n in all:
        if n == name:
            return ret
        ret += 1
    return ret


def create_request(raction, value):
    return dict(
        type="text/json",
        encoding="utf-8",
        content=dict(action=raction, value=value),
    )


def start_connection(shost, sport, request):
    addr = (shost, sport)
    # print("starting connection to", addr)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)
# endregion


class ConectionWindow(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.host = ''

        self.title("Verbindung")
        self.geometry("512x140")

        # try to get ip for server from php-script
        self.ip_am = urllib.request.urlopen('http://moja.de/public/python/getip.php').read().decode('utf8').strip()
        self.ip_parts = self.ip_am.split(".")

        self.header = Label(self, text="Verbindung:", font="Helvetica 24 bold")
        self.header.pack(side=TOP)

        self.addr_frame = Frame(self)
        self.addr_frame.pack(side=TOP)

        self.b2 = Button(self, text='START', command=lambda: [self.sethost(), self.quit()])
        self.b2.pack(side=TOP, padx=5, pady=5)

        self.entry1 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.entry1.insert(0, self.ip_parts[0])
        self.entry1.pack(side="left")

        self.l1 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.l1.pack(side="left")

        self.entry2 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.entry2.insert(0, self.ip_parts[1])
        self.entry2.pack(side="left")

        self.l2 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.l2.pack(side="left")

        self.entry3 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.entry3.insert(0, self.ip_parts[2])
        self.entry3.pack(side="left")

        self.l3 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.l3.pack(side="left")

        self.entry4 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.entry4.insert(0, self.ip_parts[3])
        self.entry4.pack(side="left")

    def get_host(self):
        return self.host

    def sethost(self):
        # global client_host
        self.host = self.entry1.get() + '.' + self.entry2.get() + '.' + self.entry3.get() + '.' + self.entry4.get()
        print(self.host)


class InitGame(tk.Tk):

    def __init__(self):

        self.host = client_host
        self.value = ''
        self.player_name = ''
        self.player_role = [0, 0, 0, 0]
        self.playernum = 0

        # region UI prepare
        tk.Tk.__init__(self)

        # region resscources
        img_char_b = Image.open(res_path + "cards/back_char.png").resize((350, 500), Image.ANTIALIAS)
        img_char_1 = Image.open(res_path + "cards/char_1.png").resize((350, 500), Image.ANTIALIAS)
        img_char_2 = Image.open(res_path + "cards/char_2.png").resize((350, 500), Image.ANTIALIAS)
        img_char_3 = Image.open(res_path + "cards/char_3.png").resize((350, 500), Image.ANTIALIAS)
        img_char_4 = Image.open(res_path + "cards/char_4.png").resize((350, 500), Image.ANTIALIAS)
        img_char_5 = Image.open(res_path + "cards/char_5.png").resize((350, 500), Image.ANTIALIAS)
        img_char_6 = Image.open(res_path + "cards/char_6.png").resize((350, 500), Image.ANTIALIAS)
        img_char_7 = Image.open(res_path + "cards/char_7.png").resize((350, 500), Image.ANTIALIAS)

        self.img_char_b = ImageTk.PhotoImage(img_char_b)
        self.img_char_1 = ImageTk.PhotoImage(img_char_1)
        self.img_char_2 = ImageTk.PhotoImage(img_char_2)
        self.img_char_3 = ImageTk.PhotoImage(img_char_3)
        self.img_char_4 = ImageTk.PhotoImage(img_char_4)
        self.img_char_5 = ImageTk.PhotoImage(img_char_5)
        self.img_char_6 = ImageTk.PhotoImage(img_char_6)
        self.img_char_7 = ImageTk.PhotoImage(img_char_7)
        # endregion

        self.title("Spielvorbereitung")  # region UI
        self.geometry("700x600")

        self.lbl1 = Label(self, text="Name", font="Helvetica 14 bold")
        self.entry_n = tk.Entry(self, width="16", justify="left", font="Helvetica 14 bold")
        self.btn_participate = Button(self, text='Teilnehmen', command=self.btn_player_enter)
        self.btn_start = Button(self, text='Spiel starten', command=self.btn_player_rdy, state=DISABLED)
        self.lbl2 = Label(self, text="Deine Rolle:", font="Helvetica 12 bold")
        self.lbl3 = Label(self, text="Spieler", font="Helvetica 12 bold")
        self.lbl4 = Label(self, text="Rolle", font="Helvetica 12 bold")
        self.lbl11 = Label(self, text="Spieler 1\nSpieler 2\nSpieler 3\nSpieler 4", font="Helvetica 12")
        self.lbl21 = Label(self, text="-\n-\n-\n-", font="Helvetica 12")
        self.role_image = Label(self, image=self.img_char_b)

        self.lbl1.grid(row=0, column=1, padx=5, pady=18, sticky=E)
        self.entry_n.grid(row=0, column=2, padx=5, pady=18, sticky=W+E)
        self.btn_participate.grid(row=0, column=3, padx=5, pady=18, sticky=W)
        self.btn_start.grid(row=0, column=4, padx=5, pady=18, sticky=W)
        self.lbl2.grid(row=1, column=1, padx=5, pady=0, sticky=W+S, columnspan=2)
        self.lbl3.grid(row=1, column=3, padx=5, pady=0, sticky=E)
        self.lbl4.grid(row=1, column=4, padx=5, pady=0, sticky=W)
        self.role_image.grid(row=2, column=1, padx=5, pady=5, columnspan=2)
        self.lbl11.grid(row=2, column=3, padx=5, pady=5, sticky=E+N)
        self.lbl21.grid(row=2, column=4, padx=5, pady=5, sticky=W+N)
        # endregion

        self.task()

    # region UI elements ###############################################################################################
    def btn_player_enter(self):
        playername = self.entry_n.get()
        if playername != "":
            self.entry_n.configure(state=DISABLED)
            self.btn_participate.configure(state=DISABLED)
            setaction("setPlayer")
            self.player_name = playername.strip()
            self.value = playername.strip()

    def btn_player_rdy(self):
        self.btn_start.configure(bg="SeaGreen1", text="Warte auf andere Spieler", state=DISABLED)
        setaction('player_rdy')
        self.value = get_player()
            # endregion

    # region game engine ###############################################################################################
    # actions
    def init_update(self, args):
        #print("init_update: " + str(args))

        # update version
        set_lv(args.get("v"))

        # player_name
        pn = args.get("player")
        self.lbl11.configure(text=pn[0]+"\n"+pn[1]+"\n"+pn[2]+"\n"+pn[3])

        # player role
        pr = args.get("player_role")
        self.lbl21.configure(text=get_role_name(pr[0]) + "\n" +
                                  get_role_name(pr[1]) + "\n" +
                                  get_role_name(pr[2]) + "\n" +
                                  get_role_name(pr[3]))

        setaction('getVersion')
        return update_intervall

    def player_set(self, args):

        # playernum
        set_player(args.get("player_num"))

        # player_name
        pn = args.get("player")
        self.lbl11.configure(text=pn[0] + "\n" + pn[1] + "\n" + pn[2] + "\n" + pn[3])

        # player role
        self.player_role = args.get("player_role")
        self.lbl21.configure(text=get_role_name(self.player_role[0]) + "\n" +
                                  get_role_name(self.player_role[1]) + "\n" +
                                  get_role_name(self.player_role[2]) + "\n" +
                                  get_role_name(self.player_role[3]))

        if get_player() > 3:
            print("to many players")
            self.lbl2.configure(text="Zu viele Spieler")
        else:
            self.btn_start.configure(state=NORMAL)
            p_num = get_player_num(pn, self.player_name)
            self.lbl2.configure(text="Deine Rolle: " + get_role_name(self.player_role[p_num]))

            switcher = {
                0: "self.role_image.configure(image=self.img_char_b)",
                1: "self.role_image.configure(image=self.img_char_1)",
                2: "self.role_image.configure(image=self.img_char_2)",
                3: "self.role_image.configure(image=self.img_char_3)",
                4: "self.role_image.configure(image=self.img_char_4)",
                5: "self.role_image.configure(image=self.img_char_5)",
                6: "self.role_image.configure(image=self.img_char_6)",
                7: "self.role_image.configure(image=self.img_char_7)",
            }
            func = switcher.get(self.player_role[p_num])
            exec(func)

        setaction('getVersion')
        return update_intervall

    def gameclient(self, m):
        print("GameCient: " + str(m))

        if m.get("response"):
            switcher = {
                "inti_update":  self.init_update,
                "player_set":   self.player_set,
            }
            # Get the function from switcher dictionary
            func = switcher.get(m.get("response"))
            u = func(m)  # execute

            if m.get("state") == "START_GAME":
                print("START_GAME")
                for widget in self.winfo_children():
                    widget.destroy()

                # this will clear frame and frame will be empty
                # if you want to hide the empty panel then
                setaction('getVersion')
        else:
            u = update_intervall
            print("FAILURE: Game Engine - No response")
        return u
    # endregion

    def get_role(self):
        return self.player_role

    def task(self):
        # create request
        request = create_request(getaction(), self.value)

        start_connection(self.host, port, request)
        update = update_intervall
        try:
            while True:
                events = sel.select(timeout=1)
                for key, mask in events:
                    message = key.data
                    try:
                        message.process_events(mask)
                        if mask == 1:

                            if message.getVersion() is not None:
                                if message.getVersion() != get_lv():
                                    setaction("get_init_update")
                                    self.value = get_player()
                                else:
                                    update = update_intervall
                            else:
                                update = self.gameclient(message.get_response())

                    except Exception:
                        print(
                            "main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}",
                        )
                        message.close()
                # Check for a socket being monitored to continue.
                if not sel.get_map():
                    break
            # eval response
            ###update = self.gameclient(message)
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")

        # if getversion -> updatetime = updateinterval else direct
        if getaction() != 'getVersion':
            update = 1
        # print("update: " + getaction(), str(update))
        # loop within mainloop
        self.after(update, self.task)


class MainGame(tk.Tk):
    def __init__(self):
        self.host = client_host
        self.value = get_player()

        self.num = thisplayer
        self.player_role = player_role

        tk.Tk.__init__(self)

        # region rescources

        # endregion

        self.title("Pandemie")  # region UI

        user32 = ctypes.windll.user32
        screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        print(str(user32.GetSystemMetrics(0)) + "x" + str(user32.GetSystemMetrics(1)))
        self.geometry(str(user32.GetSystemMetrics(0) - 100) + "x" + str(user32.GetSystemMetrics(1) - 100) + "+10+10")

        self.canvas = Canvas(self, borderwidth=1)
        self.frame = Frame(self.canvas)
        self.vsb = Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4, 4), window=self.frame, anchor="nw", tags="self.frame")
        # canvas.create_text(225, 225, font=("Helvetica", 14), text="Item 5", tags="DnD")
        self.img = PhotoImage(file=r"D:\_PROJEKTE\2020\2020_04_pandemie\data\pos_50p_pad100.png")
        self.canvas.create_image(0, 0, anchor=NW, image=self.img)

        self.canvas.create_oval(100 - 16, 261 - 16, 100 + 16, 261 + 16, outline='blue', width=3)  # San Francisco
        self.canvas.create_oval(261 - 16, 214 - 16, 261 + 16, 214 + 16, outline='blue', width=3)  # Chicago

        self.canvas.pack(expand=1, fill=tk.BOTH)

        # endregion








#canvas.create_oval(307-16,307-16,307+16,307+16, outline='blue',width = 3) #Atlanta
#canvas.create_oval(386-16,210-16,386+16,210+16, outline='blue',width = 3) #Montréal
#canvas.create_oval(483-16,225-16,483+16,225+16, outline='blue',width = 3) #New York
#canvas.create_oval(440-16,301-16,440+16,301+16, outline='blue',width = 3) #Washington
#canvas.create_oval(698-16,273-16,698+16,273+16, outline='blue',width = 3) #Madrid
#canvas.create_oval(715-16,149-16,715+16,149+16, outline='blue',width = 3) #London
#canvas.create_oval(811-16,211-16,811+16,211+16, outline='blue',width = 3) #Paris
#canvas.create_oval(842-16,124-16,842+16,124+16, outline='blue',width = 3) #Essen
#canvas.create_oval(894-16,187-16,894+16,187+16, outline='blue',width = 3) #Mailand
#canvas.create_oval(981-16,101-16,981+16,101+16, outline='blue',width = 3) #St. Petersburg
#canvas.create_oval(127-16,386-16,127+16,386+16, outline='yellow',width = 3) #Los Angeles
#canvas.create_oval(243-16,428-16,243+16,428+16, outline='yellow',width = 3) #Mexico Stadt
#canvas.create_oval(387-16,408-16,387+16,408+16, outline='yellow',width = 3) #Miami
#canvas.create_oval(376-16,534-16,376+16,534+16, outline='yellow',width = 3) #Bogotá
#canvas.create_oval(332-16,669-16,332+16,669+16, outline='yellow',width = 3) #Lima
#canvas.create_oval(349-16,810-16,349+16,810+16, outline='yellow',width = 3) #Santiago
#canvas.create_oval(481-16,785-16,481+16,785+16, outline='magenta',width = 3) #Buenos Aires
#canvas.create_oval(554-16,689-16,554+16,689+16, outline='yellow',width = 3) #Sao Paulo
#canvas.create_oval(798-16,511-16,798+16,511+16, outline='yellow',width = 3) #Lagos
#canvas.create_oval(875-16,594-16,875+16,594+16, outline='yellow',width = 3) #Kinshasa
#canvas.create_oval(948-16,724-16,948+16,724+16, outline='yellow',width = 3) #Johannisburg
#canvas.create_oval(959-16,488-16,959+16,488+16, outline='yellow',width = 3) #Khartum
#canvas.create_oval(836-16,342-16,836+16,342+16, outline='green',width = 3) #Algier
#canvas.create_oval(932-16,365-16,932+16,365+16, outline='green',width = 3) #Kairo
#canvas.create_oval(950-16,260-16,950+16,260+16, outline='green',width = 3) #Istanbul
#canvas.create_oval(1048-16,186-16,1048+16,186+16, outline='green',width = 3) #Moskau
#canvas.create_oval(1039-16,324-16,1039+16,324+16, outline='green',width = 3) #Bagdad
#canvas.create_oval(1054-16,439-16,1054+16,439+16, outline='orange',width = 3) #Riad
#canvas.create_oval(1133-16,246-16,1133+16,246+16, outline='green',width = 3) #Teheran
#canvas.create_oval(1160-16,368-16,1160+16,368+16, outline='green',width = 3) #Karatschi
#canvas.create_oval(1170-16,459-16,1170+16,459+16, outline='green',width = 3) #Mumbai
#canvas.create_oval(1251-16,330-16,1251+16,330+16, outline='green',width = 3) #Delhi
#canvas.create_oval(1269-16,524-16,1269+16,524+16, outline='green',width = 3) #Chennai
#canvas.create_oval(1339-16,360-16,1339+16,360+16, outline='green',width = 3) #Kalkutta
#canvas.create_oval(1409-16,215-16,1409+16,215+16, outline='magenta',width = 3) #Peking
#canvas.create_oval(1521-16,210-16,1521+16,210+16, outline='magenta',width = 3) #Seoul
#canvas.create_oval(1418-16,305-16,1418+16,305+16, outline='magenta',width = 3) #Shanghai
#canvas.create_oval(1609-16,260-16,1609+16,260+16, outline='magenta',width = 3) #Tokyo
#canvas.create_oval(1357-16,467-16,1357+16,467+16, outline='magenta',width = 3) #Bangkok
#canvas.create_oval(1430-16,410-16,1430+16,410+16, outline='magenta',width = 3) #Hong Kong
#canvas.create_oval(1530-16,393-16,1530+16,393+16, outline='magenta',width = 3) #Taipeh
#canvas.create_oval(1620-16,354-16,1620+16,354+16, outline='magenta',width = 3) #Osaka
#canvas.create_oval(1356-16,632-16,1356+16,632+16, outline='magenta',width = 3) #Jakarta
#canvas.create_oval(1436-16,555-16,1436+16,555+16, outline='magenta',width = 3) #Ho-Chi-MinH-Stadt
#canvas.create_oval(1558-16,549-16,1558+16,549+16, outline='magenta',width = 3) #Manila
#canvas.create_oval(1628-16,807-16,1628+16,807+16, outline='magenta',width = 3) #Sydney



        self.task_main()

    # region UI elements ###############################################################################################

    # endregion

    # region game engine ###############################################################################################
    # actions
    def update_client(self, args):
        #print("init_update: " + str(args))

        # update version
        set_lv(args.get("v"))

        # player_name
        pn = args.get("player")
        self.lbl11.configure(text=pn[0]+"\n"+pn[1]+"\n"+pn[2]+"\n"+pn[3])

        # player role
        pr = args.get("player_role")
        self.lbl21.configure(text=get_role_name(pr[0]) + "\n" +
                                  get_role_name(pr[1]) + "\n" +
                                  get_role_name(pr[2]) + "\n" +
                                  get_role_name(pr[3]))

        setaction('getVersion')
        return update_intervall

    def gameclient(self, m):
        # print("GameCient: " + str(m))

        if m.get("response"):
            switcher = {
                "update":       self.update_client,
                "player_rdy":   self.update_client,
            }
            # Get the function from switcher dictionary
            func = switcher.get(m.get("response"))
            u = func(m)  # execute
        else:
            u = update_intervall
            print("FAILURE: Game Engine - No response")
        return u
    # endregion

    def task_main(self):
        request = create_request(getaction(), self.value)
        start_connection(self.host, port, request)
        update = update_intervall
        try:
            while True:
                events = sel.select(timeout=1)
                for key, mask in events:
                    message = key.data
                    try:
                        message.process_events(mask)
                        if mask == 1:

                            if message.getVersion() is not None:
                                if message.getVersion() != get_lv():
                                    setaction("get_update")
                                    self.value = get_player()
                                else:
                                    update = update_intervall
                            else:
                                update = self.gameclient(message.get_response())

                    except Exception:
                        print(
                            "main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}",
                        )
                        message.close()
                # Check for a socket being monitored to continue.
                if not sel.get_map():
                    break
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")

        # if getversion -> updatetime = updateinterval else direct
        if getaction() != 'getVersion':
            update = 1
        # print(">> befor wait" + str(message.getVersion()))
        # loop within mainloop
        self.after(update_intervall, self.task_main)

# Conection
app = ConectionWindow()
app.mainloop()
# pass variables to local global
client_host = ConectionWindow.get_host(app)
# print(client_host)
# destroy window on exit
app.destroy()


# Preparation
app = InitGame()
app.mainloop()
# pass variables to local global
player_role = InitGame.get_role(app)
# destroy window on exit
app.destroy()

time.sleep(5)


# start game
app = MainGame()
app.mainloop()






### client without class

#!/usr/bin/env python3

import socket
import selectors
import traceback
import tkinter as tk
from tkinter import *
from tkinter.ttk import *
import urllib.request
import ctypes

from PIL import Image, ImageTk

from Pandemie import libclient

########################################################################################################################
update_intervall = 3000
port = 9999
client_host = ""
localversion = 0
action = 'getInitVersion'
########################################################################################################################

sel = selectors.DefaultSelector()


def getaction():
    global action
    return action


def setaction(newaction):
    global action
    action = newaction


def get_lv():
    global localversion
    return localversion


def set_lv(newversion):
    global localversion
    localversion = newversion


def create_request(raction, value):
    return dict(
        type="text/json",
        encoding="utf-8",
        content=dict(action=raction, value=value),
    )


def start_connection(shost, sport, request):
    addr = (shost, sport)
    # print("starting connection to", addr)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)


class ConectionWindow(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.title("Verbindung")
        self.geometry("512x140")

        # try to get ip for server from php-script
        self.ip_am = urllib.request.urlopen('http://moja.de/public/python/getip.php').read().decode('utf8').strip()
        self.ip_parts = self.ip_am.split(".")
        self.host = ''

        self.header = Label(self, text="Verbindung:", font="Helvetica 24 bold")
        self.header.pack(side=TOP)

        self.addr_frame = Frame(self)
        self.addr_frame.pack(side=TOP)

        self.b2 = Button(self, text='START', command=lambda: [self.sethost(), self.quit()])
        self.b2.pack(side=TOP, padx=5, pady=5)

        self.entry1 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.entry1.insert(0, self.ip_parts[0])
        self.entry1.pack(side="left")

        self.l1 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.l1.pack(side="left")

        self.entry2 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.entry2.insert(0, self.ip_parts[1])
        self.entry2.pack(side="left")

        self.l2 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.l2.pack(side="left")

        self.entry3 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.entry3.insert(0, self.ip_parts[2])
        self.entry3.pack(side="left")

        self.l3 = Label(self.addr_frame, text=".", font="Helvetica 32 bold")
        self.l3.pack(side="left")

        self.entry4 = Entry(self.addr_frame, width="4", justify="center", font="Helvetica 32 bold")
        self.entry4.insert(0, self.ip_parts[3])
        self.entry4.pack(side="left")

    def sethost(self):
        global client_host
        client_host = self.entry1.get() + '.' + self.entry2.get() + '.' + self.entry3.get() + '.' + self.entry4.get()
        print(client_host)


class InitGame(tk.Tk):

    def __init__(self):

        self.host = client_host
        self.value = ''
        self.player_ready = False
        self.player_name = ''

        # region UI prepare
        tk.Tk.__init__(self)
        # region resscources

        # 700 x 1000
        img_char_back = Image.open("D:/USER/Desktop/SCAN/pan/back_char.jpg").resize((350, 500), Image.ANTIALIAS)
        img_char_1 = Image.open("D:/USER/Desktop/SCAN/pan/char_1.tif").resize((350, 500), Image.ANTIALIAS)
        img_char_2 = Image.open("D:/USER/Desktop/SCAN/pan/char_2.tif").resize((350, 500), Image.ANTIALIAS)
        img_char_3 = Image.open("D:/USER/Desktop/SCAN/pan/char_3.tif").resize((350, 500), Image.ANTIALIAS)
        img_char_4 = Image.open("D:/USER/Desktop/SCAN/pan/char_4.tif").resize((350, 500), Image.ANTIALIAS)
        img_char_5 = Image.open("D:/USER/Desktop/SCAN/pan/char_5.tif").resize((350, 500), Image.ANTIALIAS)
        img_char_6 = Image.open("D:/USER/Desktop/SCAN/pan/char_6.tif").resize((350, 500), Image.ANTIALIAS)
        img_char_7 = Image.open("D:/USER/Desktop/SCAN/pan/char_7.tif").resize((350, 500), Image.ANTIALIAS)

        self.img_char_back = ImageTk.PhotoImage(img_char_back)
        self.img_char_1 = ImageTk.PhotoImage(img_char_1)
        self.img_char_2 = ImageTk.PhotoImage(img_char_2)
        self.img_char_3 = ImageTk.PhotoImage(img_char_3)
        self.img_char_4 = ImageTk.PhotoImage(img_char_4)
        self.img_char_5 = ImageTk.PhotoImage(img_char_5)
        self.img_char_6 = ImageTk.PhotoImage(img_char_6)
        self.img_char_7 = ImageTk.PhotoImage(img_char_7)
        # endregion


        self.title("Spielvorbereitung")
        self.geometry("600x600")

        self.lbl1 = Label(self, text="Name", font="Helvetica 14 bold")
        self.entry_n = tk.Entry(self, width="16", justify="left", font="Helvetica 14 bold")
        self.btn_participate = Button(self, text='Teilnehmen', command=self.btn_player_rdy)

        self.lbl2 = Label(self, text="Deine Rolle:", font="Helvetica 12 bold")
        self.lbl3 = Label(self, text="Spieler", font="Helvetica 12 bold")
        self.lbl4 = Label(self, text="Rolle", font="Helvetica 12 bold")

        self.lbl11 = Label(self, text="Spieler 1\nSpieler 2\nSpieler 3\nSpieler 4", font="Helvetica 12")
        self.lbl21 = Label(self, text="-\n-\n-\n-", font="Helvetica 12")

        self.role_image = Label(self, image=self.img_char_back)

        self.lbl1.grid(row=0, column=1, padx=5, pady=18, sticky=E)
        self.entry_n.grid(row=0, column=2, padx=5, pady=18, sticky=W+E)
        self.btn_participate.grid(row=0, column=3, padx=5, pady=18, sticky=W, columnspan=2)

        self.lbl2.grid(row=1, column=1, padx=5, pady=0, sticky=W+S, columnspan=2)
        self.lbl3.grid(row=1, column=3, padx=5, pady=0, sticky=E)
        self.lbl4.grid(row=1, column=4, padx=5, pady=0, sticky=W)

        self.role_image.grid(row=2, column=1, padx=5, pady=5, columnspan=2)

        self.lbl11.grid(row=2, column=3, padx=5, pady=5, sticky=E+N)
        self.lbl21.grid(row=2, column=4, padx=5, pady=5, sticky=W+N)
        # endregion

        self.task()

    # region UI elements ###############################################################################################
    def btn_player_rdy(self):
        playername = self.entry_n.get()
        if playername != "":
            self.player_ready = True
            self.entry_n.configure(state=DISABLED)
            setaction("setPlayer")
            self.player_name = playername.strip()
            self.value = playername.strip()
            # self.quit()
    # endregion

    # region game engine ###############################################################################################
    # actions
    def init_update(self, args):
        print("init_update: " + str(args))

        # update version
        set_lv(args.get("v"))

        # player_name
        pn = args.get("player")
        self.lbl11.configure(text=pn[0]+"\n"+pn[1]+"\n"+pn[2]+"\n"+pn[3])

        # player role
        pr = args.get("player_role")

        def role(argument):
            switcher = {
                1: "January",
                2: "February",
                3: "March",
                4: "April",
                5: "May",
                6: "June",
                7: "July"
            }
        # switcher.get(argument)



        setaction('getInitVersion')
        return update_intervall

    def gameclient(self, m):
        # print("GameCient: " + str(m))

        if m.get("response"):
            switcher = {
                "inti_update":  self.init_update,
            }
            # Get the function from switcher dictionary
            func = switcher.get(m.get("response"))
            u = func(m)  # execute
        else:
            u = update_intervall
            print("FAILURE: Game Engine - No response")

        return u
    # endregion

    def task(self):
        # create request
        request = create_request(getaction(), self.value)

        start_connection(self.host, port, request)
        try:
            while True:
                events = sel.select(timeout=1)
                for key, mask in events:
                    message = key.data
                    try:
                        message.process_events(mask)
                        if mask == 1:

                            if message.getVersion() is not None:
                                if message.getVersion() != get_lv():
                                    setaction("get_init_update")
                                else:
                                    update = update_intervall
                            else:
                                update = self.gameclient(message.get_response())

                    except Exception:
                        print(
                            "main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}",
                        )
                        message.close()
                # Check for a socket being monitored to continue.
                if not sel.get_map():
                    break
            # eval response
            ###update = self.gameclient(message)
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")

        # if getversion -> updatetime = updateinterval else direct
        if getaction() != 'getInitVersion':
            update = 1
        # print("update: " + getaction(), str(update))
        # loop within mainloop
        self.after(update, self.task)


class MainGame(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)

        self.host = client_host

        self.value = ''

        self.title("Mainframe")
        user32 = ctypes.windll.user32
        screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        print(str(user32.GetSystemMetrics(0)) + "x" + str(user32.GetSystemMetrics(1)))

        self.geometry(str(user32.GetSystemMetrics(0) - 100) + "x" + str(user32.GetSystemMetrics(1) - 100) + "+10+10")

        self.canvas = Canvas(self, borderwidth=1)
        self.frame = Frame(self.canvas)
        self.vsb = Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((4, 4), window=self.frame, anchor="nw", tags="self.frame")
        # canvas.create_text(225, 225, font=("Helvetica", 14), text="Item 5", tags="DnD")
        self.img = PhotoImage(file=r"D:\_PROJEKTE\2020\2020_04_pandemie\data\pos_50p_pad100.png")
        self.canvas.create_image(0, 0, anchor=NW, image=self.img)

        self.canvas.create_oval(100 - 16, 261 - 16, 100 + 16, 261 + 16, outline='blue', width=3)  # San Francisco
        self.canvas.create_oval(261 - 16, 214 - 16, 261 + 16, 214 + 16, outline='blue', width=3)  # Chicago

#canvas.create_oval(307-16,307-16,307+16,307+16, outline='blue',width = 3) #Atlanta
#canvas.create_oval(386-16,210-16,386+16,210+16, outline='blue',width = 3) #Montréal
#canvas.create_oval(483-16,225-16,483+16,225+16, outline='blue',width = 3) #New York
#canvas.create_oval(440-16,301-16,440+16,301+16, outline='blue',width = 3) #Washington
#canvas.create_oval(698-16,273-16,698+16,273+16, outline='blue',width = 3) #Madrid
#canvas.create_oval(715-16,149-16,715+16,149+16, outline='blue',width = 3) #London
#canvas.create_oval(811-16,211-16,811+16,211+16, outline='blue',width = 3) #Paris
#canvas.create_oval(842-16,124-16,842+16,124+16, outline='blue',width = 3) #Essen
#canvas.create_oval(894-16,187-16,894+16,187+16, outline='blue',width = 3) #Mailand
#canvas.create_oval(981-16,101-16,981+16,101+16, outline='blue',width = 3) #St. Petersburg
#canvas.create_oval(127-16,386-16,127+16,386+16, outline='yellow',width = 3) #Los Angeles
#canvas.create_oval(243-16,428-16,243+16,428+16, outline='yellow',width = 3) #Mexico Stadt
#canvas.create_oval(387-16,408-16,387+16,408+16, outline='yellow',width = 3) #Miami
#canvas.create_oval(376-16,534-16,376+16,534+16, outline='yellow',width = 3) #Bogotá
#canvas.create_oval(332-16,669-16,332+16,669+16, outline='yellow',width = 3) #Lima
#canvas.create_oval(349-16,810-16,349+16,810+16, outline='yellow',width = 3) #Santiago
#canvas.create_oval(481-16,785-16,481+16,785+16, outline='magenta',width = 3) #Buenos Aires
#canvas.create_oval(554-16,689-16,554+16,689+16, outline='yellow',width = 3) #Sao Paulo
#canvas.create_oval(798-16,511-16,798+16,511+16, outline='yellow',width = 3) #Lagos
#canvas.create_oval(875-16,594-16,875+16,594+16, outline='yellow',width = 3) #Kinshasa
#canvas.create_oval(948-16,724-16,948+16,724+16, outline='yellow',width = 3) #Johannisburg
#canvas.create_oval(959-16,488-16,959+16,488+16, outline='yellow',width = 3) #Khartum
#canvas.create_oval(836-16,342-16,836+16,342+16, outline='green',width = 3) #Algier
#canvas.create_oval(932-16,365-16,932+16,365+16, outline='green',width = 3) #Kairo
#canvas.create_oval(950-16,260-16,950+16,260+16, outline='green',width = 3) #Istanbul
#canvas.create_oval(1048-16,186-16,1048+16,186+16, outline='green',width = 3) #Moskau
#canvas.create_oval(1039-16,324-16,1039+16,324+16, outline='green',width = 3) #Bagdad
#canvas.create_oval(1054-16,439-16,1054+16,439+16, outline='orange',width = 3) #Riad
#canvas.create_oval(1133-16,246-16,1133+16,246+16, outline='green',width = 3) #Teheran
#canvas.create_oval(1160-16,368-16,1160+16,368+16, outline='green',width = 3) #Karatschi
#canvas.create_oval(1170-16,459-16,1170+16,459+16, outline='green',width = 3) #Mumbai
#canvas.create_oval(1251-16,330-16,1251+16,330+16, outline='green',width = 3) #Delhi
#canvas.create_oval(1269-16,524-16,1269+16,524+16, outline='green',width = 3) #Chennai
#canvas.create_oval(1339-16,360-16,1339+16,360+16, outline='green',width = 3) #Kalkutta
#canvas.create_oval(1409-16,215-16,1409+16,215+16, outline='magenta',width = 3) #Peking
#canvas.create_oval(1521-16,210-16,1521+16,210+16, outline='magenta',width = 3) #Seoul
#canvas.create_oval(1418-16,305-16,1418+16,305+16, outline='magenta',width = 3) #Shanghai
#canvas.create_oval(1609-16,260-16,1609+16,260+16, outline='magenta',width = 3) #Tokyo
#canvas.create_oval(1357-16,467-16,1357+16,467+16, outline='magenta',width = 3) #Bangkok
#canvas.create_oval(1430-16,410-16,1430+16,410+16, outline='magenta',width = 3) #Hong Kong
#canvas.create_oval(1530-16,393-16,1530+16,393+16, outline='magenta',width = 3) #Taipeh
#canvas.create_oval(1620-16,354-16,1620+16,354+16, outline='magenta',width = 3) #Osaka
#canvas.create_oval(1356-16,632-16,1356+16,632+16, outline='magenta',width = 3) #Jakarta
#canvas.create_oval(1436-16,555-16,1436+16,555+16, outline='magenta',width = 3) #Ho-Chi-MinH-Stadt
#canvas.create_oval(1558-16,549-16,1558+16,549+16, outline='magenta',width = 3) #Manila
#canvas.create_oval(1628-16,807-16,1628+16,807+16, outline='magenta',width = 3) #Sydney


        self.canvas.pack(expand=1, fill=tk.BOTH)

        self.task()

    def task(self):
        request = create_request('getaction()', self.value)
        start_connection(self.host, port, request)
        try:
            while True:
                events = sel.select(timeout=1)
                for key, mask in events:
                    message = key.data
                    try:
                        message.process_events(mask)
                    except Exception:
                        print(
                            "main: error: exception for",
                            f"{message.addr}:\n{traceback.format_exc()}",
                        )
                        message.close()
                # Check for a socket being monitored to continue.
                if not sel.get_map():
                    break
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")


        print(">> befor wait" + str(message.getVersion()))
        # loop within mainloop
        self.after(update_intervall, self.task)

# Conection
app = ConectionWindow()
app.mainloop()
# destroy window on exit
app.destroy()


# Preparation
app = InitGame()
app.mainloop()
# destroy window on exit
app.destroy()


# start game
app = MainGame()
app.mainloop()







#######################################################################################################################################################################################
### server without class


#!/usr/bin/env python3
# https://realpython.com/python-sockets/
# https://github.com/realpython/materials/tree/master/python-sockets-tutorial

import socket
import selectors
import traceback
import urllib.request
from Pandemie import libserver

# gamevariables ################################################################################################

host = socket.gethostname()
port = 9999

serverversion = 0
game_status = "PREP"
player = ["Andreas", "", "", ""]

########

sel = selectors.DefaultSelector()

# actions ##########################################################################################################
def get_version():
    print("switcher 1")
    content = {"result": serverversion}
    return content


def get_init_version():
    print("switcher 2")
    content = {"result": serverversion, "status": game_status}
    return content


def set_player():
    print("switcher 3")
    newname = "hi"  # request.get("value")

    n = 0
    while n < len(player):
        print(str(n)+" "+player[n])
        if player[n] != "":
            n = n + 1
        else:
            break
    if n < len(player):
        player[n] = newname

    content = {"response": "player", "player": n+1, "p0":player[0], "p1":player[1], "p2":player[2], "p3":player[3]}
    print(content)
    # content = {"response": "player"}
    return content

# action selector
def actions(argument):
    switcher = {
        "getVersion":       get_version,
        "getInitVersion":   get_init_version,
        "setPlayer":        set_player,
        }
    # Get the function from switcher dictionary
    func = switcher.get(argument.get("action"))
    # execute
    output = func()

     # default value if action is not known
    if output is None:
        output = {"result": "action not known"}
    return output

############

def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print("accepted connection from", addr)
    conn.setblocking(False)
    message = libserver.Message(sel, conn, addr)
    sel.register(conn, selectors.EVENT_READ, data=message)


# try to read external IP from webservice and store on server via php-function
external_ip = urllib.request.urlopen('https://api.ipify.org/').read().decode('utf8')
link = 'http://moja.de/public/python/setip.php?ip=' + external_ip
response = urllib.request.urlopen(link).read().decode('utf8').strip()
if response == "done":
    print("IP successfully updated " + external_ip)
else:
    print("FAILRE during IP-update")

lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Avoid bind() exception: OSError: [Errno 48] Address already in use
lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
lsock.bind((host, port))
lsock.listen()
print("listening on", (host, external_ip, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:

        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                message = key.data
                try:
                    message.process_events(mask)
                    if mask == 1:
                        req = message.get_request()
                        if req.get("action"):
                            message.set_response(actions(req))

                except Exception:
                    print(
                        "main: error: exception for",
                        f"{message.addr}:\n{traceback.format_exc()}",
                    )
                    message.close()
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()