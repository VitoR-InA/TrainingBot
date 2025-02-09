from cmd import Cmd

import Levenshtein

import os

import sqlite3

import telebot
from telebot import TeleBot, types, util

from threading import Thread


bot = TeleBot("TOKEN")


class CommandPrompt(Cmd):
    prompt = ""

    def do_admin(self, argument: str):
        "Operations on administrators\nSubcommands:\n- add user_id(s) - adding administrator(s)\n  user_id - telegram user ID, enumerates with space\n- remove / rm user_id(s) - removing administrator(s)\n  user_id - telegram user ID, enumerates with space\n- reload /r - reload the list of administrators from the file\n  Takes no arguments\n- show - display all assigned administrators\n  Takes no arguments"
        arguments = argument.split(" ")
        try: arguments.remove("")
        except ValueError: pass
        if len(arguments) > 0:
            if arguments[0] == "add":
                if not len(arguments[1:]): print("At least one user_id is expected")
                else:
                    admins_to_add = arguments[1:]
                    for admin in admins_to_add:
                        try: admin_list[int(admin)] = None
                        except ValueError: print(f"user_id must match a integer value")
                    with open(admin_list_path, "w") as admins_file:
                        admins_file.writelines(f"{admin}\n" for admin in admin_list.keys())
            elif arguments[0] in ["remove", "rm"]:
                if not len(arguments[1:]): print("At least one user_id is expected")
                else:
                    admins_to_remove = arguments[1:]
                    for admin in admins_to_remove:
                        try: admin_list.pop(int(admin))
                        except ValueError: print(f"user_id must match a integer value")
                        except KeyError: print(f"Admin {admin} not found")
                    with open(admin_list_path, "w") as admins_file:
                        admins_file.writelines(f"{admin}\n" for admin in admin_list.keys())
            elif arguments[0] in ["reload", "r"]:
                if len(arguments) > 1: print("reload does not accept additional arguments")
                else: initialize_admin_list()
            elif arguments[0] == "list":
                if len(arguments) > 1: print("list does not accept additional arguments")
                else:
                    admins_list = "\n".join(str(admin) for admin in admin_list.keys())
                    print(f"List of assigned administrators:\n{admins_list}")
            else: print(f"Unknown subcommand: {arguments[0]}")
        else: print("Subcommand expected")

    def do_connection(self, argument: str):
        "Connection operations\nSubcommands:\n- connect user_id\n user_id - telegram user ID, enumeration is not accepted\n- disconnect - disconnect from user\n Takes no arguments"
        arguments = argument.split(" ")
        try: arguments.remove("")
        except ValueError: pass
        if len(arguments) > 0:
            if arguments[0] == "connect":
                if not len(arguments[0:]) > 1: print("Expected user_id value")
                else:
                    try:
                        self.connected = int(arguments[1])
                        if self.connected not in admin_list.values():
                            bot.send_message(self.connected, "An administrator has connected to you.")
                            print("Successful connect")
                        else:
                            print("Someone has already connected to this client!")
                            self.connected = None
                    except telebot.apihelper.ApiTelegramException:
                        print("Failed to connect")
                        self.connected = None
                    except ValueError: print("user_id must match a integer value")
            elif arguments[0] == "disconnect":
                if len(arguments) > 1: print("disconnect does not accept additional arguments")
                else:
                    try:
                        if hasattr(self, "connected") and self.connected:
                            bot.send_message(self.connected, "The administrator disconnected.")
                            print("The connection was successfully terminated.")
                        else: print("There is no current connection")
                    except telebot.apihelper.ApiTelegramException: print("Failed to send disconnect message, the connection was terminated.")
                    self.connected = None
            elif arguments[0] == "list":
                if len(arguments) > 1: print("list does not accept additional arguments")
                else:
                    connections_list = "\n".join(f"{admin} : {client if client else 'No'}" for admin, client in admin_list.items())
                    print(f"List of connections:\n{connections_list}")
            else: print(f"Unknown subcommand: {arguments[0]}")
        else: print("Subcommand expected")

    def do_help(self, argument: str):
        arguments = argument.split(" ")
        try: arguments.remove("")
        except ValueError: pass
        if len(arguments) > 0:
            try: print(getattr(self, f"do_{arguments[0]}").__doc__)
            except AttributeError: print(f"Unknown command: {arguments[0]}")
        else:
            available_commands = self.get_available_commands()
            print(f"Available commands: {', '.join(available_commands)}\nTo find out their usage, type help <command>")

    def default(self, line):
        if hasattr(self, "connected") and self.connected:
            try: bot.send_message(self.connected, line)
            except Exception as exception: print(f"Unknown error: {exception}")
        else:
            available_commands = self.get_available_commands()
            ratios = [Levenshtein.ratio(ratio, line) for ratio in available_commands]
            if any(ratio > 0.6 for ratio in ratios):
                print(f"Unknown command: {line}, maybe you meant: {available_commands[ratios.index(max(ratios))]}?")
            else: print(f"Unknown command: {line}")

    def get_available_commands(self):
        return [attribute.removeprefix('do_') for attribute in dir(self) if (callable(getattr(self, attribute))) and attribute.startswith('do_')]


def initialize_sql():
    global connection, cursor
    connection = sqlite3.connect(user_data_path, check_same_thread = False)
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS contacts (user_id INTEGER PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT, phone_number TEXT NOT NULL)")
    connection.commit()

def initialize_admin_list():
    global admin_list; admin_list = {}
    if not os.path.exists(admin_list_path): open(admin_list_path, "w").close()
    with open(admin_list_path) as admins_file:
        for admin in [splitted.removesuffix("\n") for splitted in admins_file.readlines()]: admin_list[int(admin)] = None

@bot.message_handler(commands = ["start"])
def on_start_command(message):
    markup = types.ReplyKeyboardMarkup(True)
    markup.add(types.KeyboardButton("✅Get a free guide✅", request_contact = True))
    bot.send_message(message.chat.id, "Hello\! If you would like to register for the training, please fill out the [form](https://example.com/)\.",
                     "MarkDownV2", reply_markup = markup)

@bot.message_handler(commands = ["connect"])
def on_connect_command(message):
    if message.chat.id in admin_list.keys():
        try:
            client = util.extract_arguments(message.text).split(" ")[0]
            if client and int(client) != message.chat.id:
                admin_list[message.chat.id] = int(client)
                bot.send_message(admin_list[message.chat.id], "An administrator has connected to you.")
                bot.send_message(message.chat.id, "Successful connect")
            elif int(client) == message.chat.id:
                bot.send_message(message.chat.id, "You can't connect to yourself!")
            else: bot.send_message(message.chat.id, "Invalid user_id for connection!")
        except telebot.apihelper.ApiTelegramException: bot.send_message(message.chat.id, "Failed to connect")
        except ValueError: bot.send_message(message.chat.id, "user_id must match a integer value!")

@bot.message_handler(commands = ["disconnect"])
def on_disconnect_command(message):
    if message.chat.id in admin_list.keys():
        try:
            bot.send_message(admin_list[message.chat.id], "The administrator disconnected.")
            bot.send_message(message.chat.id, "The connection was successfully terminated.")
        except telebot.apihelper.ApiTelegramException: bot.send_message(message.chat.id, "Failed to send disconnect message, the connection was terminated.")
        admin_list[message.chat.id] = None

@bot.message_handler(content_types = ["contact"])
def on_contact_send(message):
    contact = message.contact
    cursor.execute("INSERT OR REPLACE INTO contacts (user_id, first_name, last_name, phone_number) VALUES (?, ?, ?, ?)",
                   (contact.user_id, contact.first_name, contact.last_name, contact.phone_number))
    connection.commit()
    bot.send_message(message.chat.id, "A request for a free guide has been sent, please wait until someone from the administration contacts you.")
    for admin in admin_list.keys(): bot.send_message(admin, f"A request for a free guide was received from {message.chat.id}, for connection `/connect {message.chat.id}`", "MarkDownV2")

@bot.message_handler(content_types = ["text"])
def on_text_message(message):
    if message.chat.id in admin_list.values():
        connected_admin = admin_list[list(admin_list.keys())[list(admin_list.values()).index(message.chat.id)]]
        bot.send_message(connected_admin, message.text)
    elif message.chat.id in admin_list.keys():
        connected_user = admin_list[message.chat.id]
        bot.send_message(connected_user, message.text)
    elif hasattr(command_prompt, "connected") and command_prompt.connected == message.chat.id: print(message.text)


if __name__ == "__main__":
    user_data_path = "Data\\UserData.db"
    admin_list_path = "Data\\AdminList.txt"

    initialize_sql()
    initialize_admin_list()

    command_prompt = CommandPrompt()
    Thread(target = command_prompt.cmdloop, daemon = True).start()

    bot.polling(non_stop = True)