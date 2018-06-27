#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This code controls a telegram bot. This bot is a kanban."""
import json
import time
import urllib
import datetime
import os

import requests
import sqlalchemy

import db
from db import Task
from contracts import contract

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

    @contract(msg='str', chat='str', status='str', returns='NoneType')
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
                create_issue(msg, chat, '')
                self.send_message(response, chat)
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


class TasksController:
    """This class controls the tasks."""

    @classmethod
    @contract(msg='str', chat='int', returns='str')
    def new_task(cls, msg, chat):
        """This function creates the new tasks."""
        task = Task(chat=chat, name=msg, status='TODO', dependencies='', parents='', priority='')
        db.session.add(task)
        db.session.commit()
        return "New task *TODO* [[{}]] {}".format(task.id, task.name)

    @classmethod
    @contract(msg='str', chat='int', returns='str')
    def rename_task(cls, msg, chat):
        """This function changes the task name."""
        text = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                text = msg.split(' ', 1)[1]

            msg = msg.split(' ', 1)[0]

        if not msg.isdigit():
            return "You must inform the task id"

        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)

            if text == '':
                return "You want to modify task {}, but you didn't provide any new text".format(task_id)

            old_text = task.name
            task.name = text
            db.session.commit()
            return "Task {} redefined from {} to {}".format(task_id, old_text, text)

    @classmethod
    @contract(msg='str', chat='int', returns='str')
    def duplicate_task(cls, msg, chat):
        """This function duplicates the task."""
        if not msg.isdigit():
            return "You must inform the task id"
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)

            dtask = Task(chat=task.chat,
                         name=task.name,
                         status=task.status,
                         dependencies=task.dependencies,
                         parents=task.parents,
                         priority=task.priority,
                         overdue=task.overdue,
                         duedate=task.duedate)
            db.session.add(dtask)

            for dependency in task.dependencies.split(',')[:-1]:
                query = db.session.query(Task).filter_by(id=int(dependency), chat=chat)
                dependency = query.one()
                dependency.parents += '{},'.format(dtask.id)

            db.session.commit()
            return "New task *TODO* [[{}]] {}".format(dtask.id, dtask.name)

    @classmethod
    @contract(msg='str', chat='int', returns='str')
    def delete_task(cls, msg, chat):
        """This function deletes tasks."""
        if not msg.isdigit():
            return "You must inform the task id"
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)
            for dependency in task.dependencies.split(',')[:-1]:
                query = db.session.query(Task).filter_by(id=int(dependency), chat=chat)
                dependency = query.one()
                dependency.parents = dependency.parents.replace('{},'.format(task.id), '')
            db.session.delete(task)
            db.session.commit()
            return "Task [[{}]] deleted".format(task_id)

    @contract(msg='str', chat='int', new_status='str', returns='str')
    def change_multiple(self, msg, chat, new_status):
        tasks = msg.split(' ')
        responses = []
        for task in tasks:
            response = self.change_status(task, chat, new_status)
            responses.append(response)
        return responses

    @contract(msg='str', chat='int', new_status='str', returns='str')
    def change_status(self, msg, chat, new_status):
        """This function changes the task status."""
        if not msg.isdigit():
            return "You must inform the task id"
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)
            task.status = new_status
            db.session.commit()
            return "*{}* task [[{}]] {}".format(new_status, task.id, task.name)

    @contract(task='str', returns='str')
    def get_priority(self, task):
        if task.priority == 'low':
            return '\U00002755'
        elif task.priority == 'medium':
            return '\U00002757'
        elif task.priority == 'high':
            return '\U0000203C'

        return ''

    @contract(chat='str', returns='str')
    def list_overdue(self, chat):
        tasks = ''
        overdue = True
        query = db.session.query(Task).filter_by(overdue=overdue, chat=chat).order_by(Task.id)
        for task in query.all():
            tasks += '[[{}]] {}\n'.format(task.id, task.name)

        return tasks

    @contract(chat='str', status='str', returns='str')
    def filter_by_status(self, chat, status):
        """This function orders the tasks using the status."""
        tasks = ''
        overdue = False
        query = db.session.query(Task).filter_by(status=status, overdue=overdue, chat=chat).order_by(Task.id)
        for task in query.all():
            tasks += '[[{}]] {}\n'.format(task.id, task.name)
        return tasks

    @contract(chat='str', priority='str', returns='str')
    def filter_by_priority(self, chat, priority):
        """This method orders tasks by their priority."""
        tasks = ''
        query = db.session.query(Task).filter_by(priority=priority, chat=chat).order_by(Task.id)
        for task in query.all():
            tasks += '[[{}]] {}\n'.format(task.id, task.name)
        return tasks

    @contract(chat='str', returns='str')
    def list_default(self, chat):
        task_list = ''

        task_list += '\U0001F4CB Task List\n'
        query = db.session.query(Task).filter_by(parents='', chat=chat).order_by(Task.id)

        today = None
        NO_TIME = 0
        difference = ''

        today = datetime.date.today()

        for task in query.all():
            if task.duedate != None:
                difference = task.duedate - today

            if task.duedate != None and difference.days < NO_TIME:
                task.overdue = True
            else:
                task.overdue = False

            print(task.overdue)

            icon = '\U0001F195'
            if task.status == 'DOING':
                icon = '\U000023FA'
            elif task.status == 'DONE':
                icon = '\U00002611'

            task_list += '[[{}]] {} {}\n'.format(task.id, icon, task.name)
            task_list += deps_text(task, chat)

        return task_list

    @contract(chat='str', returns='str')
    def list_by_status(self, chat):
        tasks_by_status = ''

        tasks_by_status += '\U0001F4DD _Status_\n'
        tasks_by_status += '\n\U0001F195 *TODO*\n'
        tasks_by_status += self.filter_by_status(chat, 'TODO')
        tasks_by_status += '\n\U000023FA *DOING*\n'
        tasks_by_status += self.filter_by_status(chat, 'DOING')
        tasks_by_status += '\n\U00002611 *DONE*\n'
        tasks_by_status += self.filter_by_status(chat, 'DONE')
        tasks_by_status += '\n\U0001F198 *OVERDUE*\n'
        tasks_by_status += self.list_overdue(chat)

        return tasks_by_status

    @contract(chat='str', returns='str')
    def list_by_priority(self, chat):
        tasks_by_priority = ''

        tasks_by_priority += '_Priorities_\n'
        tasks_by_priority += '*HIGH*\n'
        tasks_by_priority += self.filter_by_priority(chat, 'high')
        tasks_by_priority += '*MEDIUM*\n'
        tasks_by_priority += self.filter_by_priority(chat, 'medium')
        tasks_by_priority += '*LOW*\n'
        tasks_by_priority += self.filter_by_priority(chat, 'low')

        return tasks_by_priority

    @contract(msg='str', chat='str', returns='str')
    def list_tasks(self, msg, chat):
        """This function lists the tasks."""
        task_list = ''
        tasks_by_status = ''
        tasks_by_priority = ''
        list_messages = []

        task_list += self.list_default(chat)
        list_messages.append(task_list)

        tasks_by_status += self.list_by_status(chat)
        list_messages.append(tasks_by_status)

        tasks_by_priority += self.list_by_priority(chat)
        list_messages.append(tasks_by_priority)
        return list_messages

    @classmethod
    @contract(msg='str', chat='str', returns='str')
    def depends_on(cls, msg, chat):
        """This function controls the task dependencies."""
        text = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                text = msg.split(' ', 1)[1]
            msg = msg.split(' ', 1)[0]

        if not msg.isdigit():
            return "You must inform the task id"
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)

            if text == '':
                for i in task.dependencies.split(',')[:-1]:
                    i = int(i)
                    query = db.session.query(Task).filter_by(id=i, chat=chat)
                    task_dep = query.one()
                    task_dep.parents = task_dep.parents.replace('{},'.format(task.id), '')

                task.dependencies = ''
                return "Dependencies removed from task {}".format(task_id)
            elif dependency_exist(text, task_id):
                return "Task {} already have a dependency of task {}".format(text, task_id)
            else:
                for depid in text.split(' '):
                    if not depid.isdigit():
                        return "All dependencies ids must be numeric, and not {}".format(depid)
                    else:
                        depid = int(depid)
                        query = db.session.query(Task).filter_by(id=depid, chat=chat)
                        try:
                            taskdep = query.one()
                            taskdep.parents += str(task.id) + ','
                        except sqlalchemy.orm.exc.NoResultFound:
                            return "_404_ Task {} not found x.x".format(depid)
                            continue

                        deplist = task.dependencies.split(',')
                        if str(depid) not in deplist:
                            task.dependencies += str(depid) + ','

            db.session.commit()
            return "Task {} dependencies up to date".format(task_id)

    @classmethod
    @contract(msg='str', chat='str', returns='str')
    def set_priority(cls, msg, chat):
        """This function controls the task priority."""
        text = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                text = msg.split(' ', 1)[1]
            msg = msg.split(' ', 1)[0]

        if not msg.isdigit():
            return "You must inform the task id"
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)

            if text == '':
                task.priority = ''
                return "_Cleared_ all priorities from task {}".format(task_id)
            else:
                if text.lower() not in ['high', 'medium', 'low']:
                    return "The priority *must be* one of the following: high, medium, low"
                else:
                    task.priority = text.lower()
                    return "*Task {}* priority has priority *{}*".format(task_id, text.lower())
            db.session.commit()

    @classmethod
    @contract(msg='str', chat='str', returns='str')
    def set_duedate(cls, msg, chat):
        """This function controls the task duedate."""
        text = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                text = msg.split(' ', 1)[1]
            msg = msg.split(' ', 1)[0]

        if not msg.isdigit():
            return "You must inform the task id"
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)

            if text == '':
                task.duedate = None
                db.session.commit()
                return "_Cleared_ all duedate from task {}".format(task_id)
            else:
                print(task.duedate)
                duedate = ''
                today = ''
                diference = 0

                duedate = text.split('/')
                duedate = datetime.date(int(duedate[2]), int(duedate[1]), int(duedate[0]))
                today = datetime.date.today()

                diference = (duedate - today).days

                if diference < 0:
                    return "The duedate *must be* greater than or equal today's date"
                else:
                    task.duedate = duedate
                    task.overdue = False
                    db.session.commit()
                    return "*Task {}* duedate has priority *{}*".format(task_id, duedate)



def dependency_exist(task, task_dependecy):
    query = db.session.query(Task).filter_by(id=task)
    task_dep = query.one()
    dependencies_task = task_dep.dependencies.split(",")

    return str(task_dependecy) in dependencies_task

def deps_text(task, chat, preceed=''):
    text = ''

    for i in range(len(task.dependencies.split(',')[:-1])):
        line = preceed
        query = db.session.query(Task).filter_by(
            id=int(task.dependencies.split(',')[:-1][i]), chat=chat)
        dep = query.one()

        icon = '\U0001F195'
        if dep.status == 'DOING':
            icon = '\U000023FA'
        elif dep.status == 'DONE':
            icon = '\U00002611'

        if i + 1 == len(task.dependencies.split(',')[:-1]):
            line += '└── [[{}]] {} {}\n'.format(dep.id, icon, dep.name)
            line += deps_text(dep, chat, preceed + '    ')
        else:
            line += '├── [[{}]] {} {}\n'.format(dep.id, icon, dep.name)
            line += deps_text(dep, chat, preceed + '│   ')

        text += line

    return text        

REPOSITORY_OWNER='TecProg-20181'
REPOSITORY_NAME='T--kanbot'

USERNAME = ''
PASSWORD = ''


def user_login():
    """This function gets the bot login."""
    with open('login.txt') as login_file:
        login = login_file.read().split('\n')
        return login

def create_issue(msg, chat, body=None):
    """This function creates an issue on github."""
    
    api = Api()

    login = user_login()

    USERNAME = login[0]
    PASSWORD = login[1]

    url = 'https://api.github.com/repos/%s/%s/issues' % (REPOSITORY_OWNER, REPOSITORY_NAME)
    
    session = requests.Session()

    session.auth = (USERNAME, PASSWORD)

    issue = {'title': msg,
             'body': body}

    payload = json.dumps(issue)
    response = session.post(url, payload)

    if response.status_code == 201:
        api.send_message('Successfully created Issue {0:s}'.format(msg), chat)
    else:
        api.send_message('Could not create Issue {0:s}'.format(msg), chat)
        print ('Response:', response.content)

def main():
    """This function controls the bot. """
    
    last_update_id = None
    api = Api()

    while True:
        print("Updates")
        updates = api.get_updates(last_update_id)

        if updates["result"]:
            last_update_id = api.get_last_update_id(updates) + 1
            api.handle_updates(updates)

        time.sleep(0.5)

if __name__ == '__main__':
    main()
