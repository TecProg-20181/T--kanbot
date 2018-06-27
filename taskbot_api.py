import json
import urllib
import requests

from contracts import contract

from tasks_controller import TasksController
from github_integration import GithubIntegration

class Api:
    """This class controls the API."""
    def __init__(self):
        self.token = self.get_token()
        self.url = "https://api.telegram.org/bot{}/".format(self.token)
        self.controller = TasksController()
        self.help = """
                    /new NOME
                    /todo ID
                    /doing ID
                    /done ID
                    /delete ID
                    /list
                    /rename ID NOME
                    /dependson ID ID...
                    /duplicate ID
                    /priority ID PRIORITY{low, medium, high}
                    /duedate ID DATE{dd/mm/yyyy}
                    /help
                    """
                    
    @classmethod
    @contract(returns='str')
    def get_token(cls):
        """This function gets the bot token."""

        with open('token.txt') as token_file:
            token = token_file.read()
            return token

    @classmethod
    @contract(url='str', returns='str')
    def get_url(cls, url):
        """This function gets the bot url."""
        response = requests.get(url)
        content = response.content.decode("utf8")
        return content
    
    @contract(url='str', returns='dict')
    def get_json_from_url(self, url):
        """This function gets de json from url."""
        content = self.get_url(url)
        json_response = json.loads(content)
        return json_response

    # @contract(offset='NoneType', returns='dict')
    def get_updates(self, offset=None):
        """This function gets the bot updates."""
        url = self.url + "getUpdates?timeout=100"
        if offset:
            url += "&offset={}".format(offset)
        json_response = self.get_json_from_url(url)
        return json_response

    @contract(text='str', chat_id='int', reply_markup='NoneType', returns='None')
    def send_message(self, text, chat_id, reply_markup=None):
        """This function sends messages for the user."""
        text = urllib.parse.quote_plus(text)
        url = self.url + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
        if reply_markup:
            url += "&reply_markup={}".format(reply_markup)
        self.get_url(url)

    @classmethod
    @contract(updates='dict', returns='int')
    def get_last_update_id(cls, updates):
        """This function gets the id of the last update."""
        update_ids = []
        for update in updates["result"]:
            update_ids.append(int(update["update_id"]))

        return max(update_ids)

    @contract(msg='str', chat='int', status='str', returns='NoneType')
    def handle_status_change(self, msg, chat, status):
        response_list = self.controller.change_multiple(msg, chat, status)
        for response in response_list:
            self.send_message(response, chat)

    @contract(updates='dict', returns='NoneType')
    def handle_updates(self, updates):
        """This function controls the updates."""
        for update in updates["result"]:
            if 'message' in update:
                message = update['message']
            elif 'edited_message' in update:
                message = update['edited_message']
            else:
                print ('Can\'t process! {}').format(update)
                return

            print(message)

            command = message["text"].split(" ", 1)[0]
            msg = ''
            if len(message["text"].split(" ", 1)) > 1:
                msg = message["text"].split(" ", 1)[1].strip()

            chat = message["chat"]["id"]

            print(command, msg, chat)

            if command == '/new':
                response = self.controller.new_task(msg, chat)
                github = GithubIntegration()
                github_response = github.create_issue(msg, '')
                self.send_message(response, chat)
                self.send_message(github_response, chat)                
            elif command == '/rename':
                response = self.controller.rename_task(msg, chat)
                self.send_message(response, chat)
            elif command == '/duplicate':
                response = self.controller.duplicate_task(msg, chat)
                self.send_message(response, chat)
            elif command == '/delete':
                response = self.controller.delete_task(msg, chat)
                self.send_message(response, chat)
            elif command == '/todo':
                status = 'TODO'
                self.handle_status_change(msg, chat, status)
            elif command == '/doing':
                status = 'DOING'
                self.handle_status_change(msg, chat, status)
            elif command == '/done':
                status = 'DONE'
                self.handle_status_change(msg, chat, status)
            elif command == '/list':
                response_list = self.controller.list_tasks(msg, chat)
                for response in response_list:
                    self.send_message(response, chat)
            elif command == '/dependson':
                response = self.controller.depends_on(msg, chat)
                self.send_message(response, chat)
            elif command == '/priority':
                response = self.controller.set_priority(msg, chat)
                self.send_message(response, chat)
            elif command == '/duedate':
                response = self.controller.set_duedate(msg, chat)
                self.send_message(response, chat)
            elif command == '/start':
                self.send_message("Welcome! Here is a list of things you can do.", chat)
                self.send_message(self.help, chat)
            elif command == '/help':
                self.send_message("Here is a list of things you can do.", chat)
                self.send_message(self.help, chat)
            else:
                self.send_message("I'm sorry dave. I'm afraid I can't do that.", chat)
