"""Helper functions for navigating the Melee menus in ways that would be
cumbersome to do on your own. The goal here is to get you into the game
as easily as possible so you don't have to worry about it. Your AI should
concentrate on playing the game, not futzing with menus.
"""
from melee import enums
import math

class MenuHelper():
    name_tag_index = 0
    inputs_live = False

    def menu_helper_simple(gamestate,
                            controller,
                            port,
                            character_selected,
                            stage_selected,
                            connect_code,
                            autostart=False,
                            swag=True):
        """Siplified menu helper function to get you through the menus and into a game

        Does everything for you but play the game. Gets you to the right menu screen, picks
        your character, chooses the stage, enters connect codes, etc...

        Args:
            gamestate (gamestate.GameState): The current GameState for this frame
            controller (controller.Controller): A Controller object that the bot will press buttons on
            character_selected (enums.Character): The character your bot will play as
            stage_selected (enums.Stage): The stage your bot will choose to play on
            connect_code (str): The connect code to direct match with. Leave blank for VS mode.
            autostart (bool): Automatically start the game when it's ready.
                Useful for BotvBot matches where no human is there to start it.
            swag (bool): What it sounds like
        """

        # If we're at the character select screen, choose our character
        if gamestate.menu_state in [enums.Menu.CHARACTER_SELECT, enums.Menu.SLIPPI_ONLINE_CSS]:
            if gamestate.submenu == enums.SubMenu.NAME_ENTRY_SUBMENU:
                MenuHelper.name_tag_index = MenuHelper.enter_direct_code(gamestate=gamestate,
                                                           controller=controller,
                                                           connect_code=connect_code,
                                                           index=MenuHelper.name_tag_index)
            else:
                MenuHelper.choose_character(character=character_selected,
                                            gamestate=gamestate,
                                            port=port,
                                            controller=controller,
                                            swag=True,
                                            start=autostart)
        # If we're at the postgame scores screen, spam START
        elif gamestate.menu_state == enums.Menu.POSTGAME_SCORES:
            MenuHelper.skip_postgame(controller=controller)
        # If we're at the stage select screen, choose a stage
        elif gamestate.menu_state == enums.Menu.STAGE_SELECT:
            MenuHelper.choose_stage(stage=stage_selected,
                                    gamestate=gamestate,
                                    controller=controller)
        elif gamestate.menu_state == enums.Menu.MAIN_MENU:
            if connect_code:
                MenuHelper.choose_direct_online(gamestate=gamestate, controller=controller)
            else:
                MenuHelper.choose_versus_mode(gamestate=gamestate, controller=controller)

    def enter_direct_code(gamestate, controller, connect_code, index):
        """At the nametag entry screen, enter the given direct connect code and exit

        Args:
            gamestate (gamestate.GameState): The current GameState for this frame
            controller (controller.Controller): A Controller object to press buttons on
            connect_code (str): The connect code to direct match with. Leave blank for VS mode.
            index (int): Current name tag index

        Returns:
            new index (incremented if we entered a new character)
        """
        # The name entry screen is dead for the first few frames
        #   So if the first character is A, then the input can get eaten
        #   Account for this by making sure we can move off the letter first
        if gamestate.menu_selection != 45:
            MenuHelper.inputs_live = True

        if not MenuHelper.inputs_live:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
            return index

        # Let the controller go every other frame. Makes the logic below easier
        if gamestate.frame % 2 == 0:
            controller.release_all()
            return index

        if len(connect_code) == index:
            controller.press_button(enums.Button.BUTTON_START)
            return index

        target_character = connect_code[index]
        target_code = 45
        column = "ABCDEFGHIJ".find(target_character)
        if column != -1:
            target_code = 45 - (column * 5)
        column = "KLMNOPQRST".find(target_character)
        if column != -1:
            target_code = 46 - (column * 5)
        column = "UVWXYZ   #".find(target_character)
        if column != -1:
            target_code = 47 - (column * 5)
        column = "0123456789".find(target_character)
        if column != -1:
            target_code = 48 - (column * 5)

        if gamestate.menu_selection == target_code:
            controller.press_button(enums.Button.BUTTON_A)
            return index + 1

        if gamestate.menu_selection == 57:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            return index

        if gamestate.menu_selection < target_code:
            diff = target_code - gamestate.menu_selection
            if diff < 5:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            else:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
        else:
            diff = target_code - gamestate.menu_selection
            if diff > 5:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
            else:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)

        return index

    def choose_character(character, gamestate, port, controller, swag=False, start=False):
        """Choose a character from the character select menu

        Args:
            character (enums.Character): The character you want to pick
            gamestate (gamestate.GameState): The current gamestate
            controller (controller.Controller): The controller object to press buttons on
            swag (bool): Pick random until you get the character
            start (bool): Automatically start the match when it's ready

        Note:
            Intended to be called each frame while in the character select menu

        Note:
            All controller cursors must be above the character level for this
            to work. The match won't start otherwise.
        """
        # Figure out where the character is on the select screen
        # NOTE: This assumes you have all characters unlocked
        # Positions will be totally wrong if something is not unlocked
        ai_state = gamestate.player[port]

        # Discover who is the opponent
        opponent_state = None
        for i, player in gamestate.player.items():
            # TODO For now, just assume they're the first controller port that isn't us
            if i != port:
                opponent_state = player
                break

        cursor_x, cursor_y = ai_state.cursor_x, ai_state.cursor_y
        coin_down = ai_state.coin_down
        character_selected = ai_state.character_selected
        isSlippiCSS = False
        if gamestate.menu_state == enums.Menu.SLIPPI_ONLINE_CSS:
            cursor_x, cursor_y = gamestate.player[1].cursor_x, gamestate.player[1].cursor_y
            isSlippiCSS = True
            character_selected = gamestate.player[1].character_selected

        row = character.value // 9
        column = character.value % 9
        #The random slot pushes the bottom row over a slot, so compensate for that
        if row == 2:
            column = column+1
        #re-order rows so the math is simpler
        row = 2-row

        #Go to the random character
        if swag:
            row = 0
            column = 0

        #Height starts at 1, plus half a box height, plus the number of rows
        target_y = 1 + 3.5 + (row * 7.0)
        #Starts at -32.5, plus half a box width, plus the number of columns
        #NOTE: Technically, each column isn't exactly the same width, but it's close enough
        target_x = -32.5 + 3.5 + (column * 7.0)
        #Wiggle room in positioning character
        wiggleroom = 1.5

        # We are already set, so let's taunt our opponent
        if character_selected == character and swag and not start:
            delta_x = 3 * math.cos(gamestate.frame / 1.5)
            delta_y = 3 * math.sin(gamestate.frame / 1.5)

            target_x = opponent_state.cursor_x + delta_x
            target_y = opponent_state.cursor_y + delta_y

            diff_x = abs(target_x - cursor_x)
            diff_y = abs(target_y - cursor_y)
            larger_magnitude = max(diff_x, diff_y)

            # Scale down values to between 0 and 1
            x = diff_x / larger_magnitude
            y = diff_y / larger_magnitude

            # Now scale down to be between .5 and 1
            if cursor_x < target_x:
                x = (x/2) + 0.5
            else:
                x = 0.5 - (x/2)
            if cursor_y < target_y:
                y = (y/2) + 0.5
            else:
                y = 0.5 - (y/2)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, x, y)

            if isSlippiCSS:
                controller.press_button(enums.Button.BUTTON_START)
            return

        #We want to get to a state where the cursor is NOT over the character,
        # but it's selected. Thus ensuring the token is on the character
        isOverCharacter = abs(cursor_x - target_x) < wiggleroom and \
            abs(cursor_y - target_y) < wiggleroom

        #Don't hold down on B, since we'll quit the menu if we do
        if controller.prev.button[enums.Button.BUTTON_B] == True:
            controller.release_button(enums.Button.BUTTON_B)
            return

        #If character is selected, and we're in of the area, and coin is down, then we're good
        if (character_selected == character) and coin_down:
            if start and gamestate.ready_to_start and \
                controller.prev.button[enums.Button.BUTTON_START] == False:
                controller.press_button(enums.Button.BUTTON_START)
                return
            else:
                controller.release_all()
                return

        #release start in addition to anything else
        controller.release_button(enums.Button.BUTTON_START)

        #If we're in the right area, select the character
        if isOverCharacter:
            #If we're over the character, but it isn't selected,
            #   then the coin must be somewhere else.
            #   Press B to reclaim the coin

            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, .5)

            # The slippi menu doesn't have a coin down. We can make-do
            if isSlippiCSS and (character_selected != character):
                if gamestate.frame % 5 == 0:
                    controller.press_button(enums.Button.BUTTON_B)
                    controller.release_button(enums.Button.BUTTON_A)
                    return
                else:
                    controller.press_button(enums.Button.BUTTON_A)
                    controller.release_button(enums.Button.BUTTON_B)
                    return

            if (character_selected != character) and coin_down:
                controller.press_button(enums.Button.BUTTON_B)
                controller.release_button(enums.Button.BUTTON_A)
                return
            #Press A to select our character
            else:
                if controller.prev.button[enums.Button.BUTTON_A] == False:
                    controller.press_button(enums.Button.BUTTON_A)
                    return
                else:
                    controller.release_button(enums.Button.BUTTON_A)
                    return
        else:
            #Move in
            controller.release_button(enums.Button.BUTTON_A)
            #Move up if we're too low
            if cursor_y < target_y - wiggleroom:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
                return
            #Move down if we're too high
            if cursor_y > target_y + wiggleroom:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
                return
            #Move right if we're too left
            if cursor_x < target_x - wiggleroom:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
                return
            #Move left if we're too right
            if cursor_x > target_x + wiggleroom:
                controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
                return
        controller.release_all()

    def choose_stage(stage, gamestate, controller):
        """Choose a stage from the stage select menu

        Intended to be called each frame while in the stage select menu

        Args:
            stage (enums.Stage): The stage you want to select
            gamestate (gamestate.GameState): The current gamestate
            controller (controller.Controller): The controller object to press
        """
        if gamestate.frame < 20:
            controller.release_all()
            return
        target_x, target_y = 0, 0
        if stage == enums.Stage.BATTLEFIELD:
            target_x, target_y = 1, -9
        if stage == enums.Stage.FINAL_DESTINATION:
            target_x, target_y = 6.7, -9
        if stage == enums.Stage.DREAMLAND:
            target_x, target_y = 12.5, -9
        if stage == enums.Stage.POKEMON_STADIUM:
            target_x, target_y = 15, 3.5
        if stage == enums.Stage.YOSHIS_STORY:
            target_x, target_y = 3.5, 15.5
        if stage == enums.Stage.FOUNTAIN_OF_DREAMS:
            target_x, target_y = 10, 15.5
        if stage == enums.Stage.RANDOM_STAGE:
            target_x, target_y = -13.5, 3.5

        #Wiggle room in positioning cursor
        wiggleroom = 1.5
        #Move up if we're too low
        if gamestate.stage_select_cursor_y < target_y - wiggleroom:
            controller.release_button(enums.Button.BUTTON_A)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
            return
        #Move downn if we're too high
        if gamestate.stage_select_cursor_y > target_y + wiggleroom:
            controller.release_button(enums.Button.BUTTON_A)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            return
        #Move right if we're too left
        if gamestate.stage_select_cursor_x < target_x - wiggleroom:
            controller.release_button(enums.Button.BUTTON_A)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
            return
        #Move left if we're too right
        if gamestate.stage_select_cursor_x > target_x + wiggleroom:
            controller.release_button(enums.Button.BUTTON_A)
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
            return

        #If we get in the right area, press A
        controller.press_button(enums.Button.BUTTON_A)

    def skip_postgame(controller):
        """ Spam the start button """
        #Alternate pressing start and letting go
        if controller.prev.button[enums.Button.BUTTON_START] == False:
            controller.press_button(enums.Button.BUTTON_START)
        else:
            controller.release_button(enums.Button.BUTTON_START)

    def change_controller_status(controller, gamestate, targetport, port, status, character=None):
        """Switch a given player's controller to be of the given state

        Note:
            There's a condition on this you need to know. The way controllers work
            in Melee, if a controller is plugged in, only that player can make the status
            go to uplugged. If you've ever played Melee, you probably know this. If your
            friend walks away, you have to press the A button on THEIR controller. (or
            else actually unplug the controller) No way around it."""
        ai_state = gamestate.player[port]
        target_x, target_y = 0, -2.2
        if targetport == 1:
            target_x = -31.5
        if targetport == 2:
            target_x = -16.5
        if targetport == 3:
            target_x = -1
        if targetport == 4:
            target_x = 14
        wiggleroom = 1.5

        correctcharacter = (character is None) or \
            (character == gamestate.player[targetport].character_selected)

        #if we're in the right state already, do nothing
        if gamestate.player[targetport].controller_status == status and correctcharacter:
            controller.release_all()
            return

        #Move up if we're too low
        if ai_state.cursor_y < target_y - wiggleroom:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 1)
            return
        #Move downn if we're too high
        if ai_state.cursor_y > target_y + wiggleroom:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            return
        #Move right if we're too left
        if ai_state.cursor_x < target_x - wiggleroom:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 1, .5)
            return
        #Move left if we're too right
        if ai_state.cursor_x > target_x + wiggleroom:
            controller.tilt_analog(enums.Button.BUTTON_MAIN, 0, .5)
            return

        #If we get in the right area, press A until we're in the right state
        controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, .5)
        if not controller.prev.button[enums.Button.BUTTON_A]:
            controller.press_button(enums.Button.BUTTON_A)
        else:
            controller.release_button(enums.Button.BUTTON_A)

    def choose_versus_mode(gamestate, controller):
        """Helper function to bring us into the versus mode menu

        Args:
            gamestate (gamestate.GameState): The current gamestate
            controller (controller.Controller): The controller to press buttons on
        """
        # Let the controller go every other frame. Makes the logic below easier
        if gamestate.frame % 2 == 0:
            controller.release_all()
            return

        if gamestate.menu_state == enums.Menu.MAIN_MENU:
            if gamestate.submenu == enums.SubMenu.MAIN_MENU_SUBMENU:
                if gamestate.menu_selection == 1:
                    controller.press_button(enums.Button.BUTTON_A)
                else:
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            elif gamestate.submenu == enums.SubMenu.VS_MODE_SUBMENU:
                if gamestate.menu_selection == 0:
                    controller.press_button(enums.Button.BUTTON_A)
                else:
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            else:
                controller.press_button(enums.Button.BUTTON_B)
        elif gamestate.menu_state == enums.Menu.PRESS_START:
            controller.press_button(enums.Button.BUTTON_START)
        else:
            controller.release_all()

    def choose_direct_online(gamestate, controller):
        """Helper function to bring us into the direct connect online menu

        Args:
            gamestate (gamestate.GameState): The current gamestate
            controller (controller.Controller): The controller to press buttons on
        """
        # Let the controller go every other frame. Makes the logic below easier
        if gamestate.frame % 2 == 0:
            controller.release_all()
            return

        if gamestate.menu_state == enums.Menu.MAIN_MENU:
            if gamestate.submenu == enums.SubMenu.ONLINE_PLAY_SUBMENU:
                if gamestate.menu_selection == 2:
                    controller.press_button(enums.Button.BUTTON_A)
                else:
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)
            elif gamestate.submenu == enums.SubMenu.MAIN_MENU_SUBMENU:
                controller.press_button(enums.Button.BUTTON_A)
            elif gamestate.submenu == enums.SubMenu.ONEP_MODE_SUBMENU:
                if gamestate.menu_selection == 2:
                    controller.press_button(enums.Button.BUTTON_A)
                else:
                    controller.tilt_analog(enums.Button.BUTTON_MAIN, .5, 0)

            elif gamestate.submenu == enums.SubMenu.NAME_ENTRY_SUBMENU:
                pass
            else:
                controller.press_button(enums.Button.BUTTON_B)
        elif gamestate.menu_state == enums.Menu.PRESS_START:
            controller.press_button(enums.Button.BUTTON_START)
        else:
            controller.release_all()
