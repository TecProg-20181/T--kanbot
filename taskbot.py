#!/usr/bin/env python3

import json
import time
import urllib

import requests
import sqlalchemy

import db
from db import Task

class Api:
    def __init__(self):
        self.TOKEN = self.get_token()
        self.URL = "https://api.telegram.org/bot{}/".format(self.TOKEN)
        self.HELP = """
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
                    /help
                    """

    def get_token(self):
        with open('token.txt') as token_file:
            token = token_file.read()
            return token

    def get_url(self, url):
        response = requests.get(url)
        content = response.content.decode("utf8")
        return content

    def get_json_from_url(self, url):
        content = self.get_url(url)
        json_response = json.loads(content)
        return json_response

    def get_updates(self, offset=None):
        url = self.URL + "getUpdates?timeout=100"
        if offset:
            url += "&offset={}".format(offset)
        json_response = self.get_json_from_url(url)
        return json_response

    def send_message(self, text, chat_id, reply_markup=None):
        text = urllib.parse.quote_plus(text)
        url = self.URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
        if reply_markup:
            url += "&reply_markup={}".format(reply_markup)
        self.get_url(url)

    def get_last_update_id(self, updates):
        update_ids = []
        for update in updates["result"]:
            update_ids.append(int(update["update_id"]))

        return max(update_ids)
    

class TasksController:
    def __init__(self, api):
        self.api = api

    def new_task(self, msg, chat):
        task = Task(chat=chat, name=msg, status='TODO', dependencies='', parents='', priority='')
        db.session.add(task)
        db.session.commit()
        return "New task *TODO* [[{}]] {}".format(task.id, task.name)

    def rename_task(self, msg, chat):
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

    def handle_updates(self, updates):
        for update in updates["result"]:
            if 'message' in update:
                message = update['message']
            elif 'edited_message' in update:
                message = update['edited_message']
            else:
                print('Can\'t process! {}'.format(update))
                return

            command = message["text"].split(" ", 1)[0]
            msg = ''
            if len(message["text"].split(" ", 1)) > 1:
                msg = message["text"].split(" ", 1)[1].strip()

            chat = message["chat"]["id"]

            print(command, msg, chat)

            if command == '/new':
                response = self.new_task(msg, chat)
                self.api.send_message(response, chat)

            elif command == '/rename':
                response = self.rename_task(msg, chat)
                self.api.send_message(response, chat)

            elif command == '/duplicate':
                if not msg.isdigit():
                    self.api.send_message("You must inform the task id", chat)
                else:
                    task_id = int(msg)
                    query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                    try:
                        task = query.one()
                    except sqlalchemy.orm.exc.NoResultFound:
                        self.api.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                        return

                    dtask = Task(chat=task.chat, name=task.name, status=task.status, dependencies=task.dependencies,
                                parents=task.parents, priority=task.priority, duedate=task.duedate)
                    db.session.add(dtask)

                    for dependency in task.dependencies.split(',')[:-1]:
                        query = db.session.query(Task).filter_by(id=int(dependency), chat=chat)
                        dependency = query.one()
                        dependency.parents += '{},'.format(dtask.id)

                    db.session.commit()
                    self.api.send_message("New task *TODO* [[{}]] {}".format(dtask.id, dtask.name), chat)

            elif command == '/delete':
                if not msg.isdigit():
                    self.api.send_message("You must inform the task id", chat)
                else:
                    task_id = int(msg)
                    query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                    try:
                        task = query.one()
                    except sqlalchemy.orm.exc.NoResultFound:
                        self.api.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                        return
                    for dependency in task.dependencies.split(',')[:-1]:
                        query = db.session.query(Task).filter_by(id=int(dependency), chat=chat)
                        dependency = query.one()
                        dependency.parents = dependency.parents.replace('{},'.format(task.id), '')
                    db.session.delete(task)
                    db.session.commit()
                    self.api.send_message("Task [[{}]] deleted".format(task_id), chat)

            elif command == '/todo':
                if not msg.isdigit():
                    self.api.send_message("You must inform the task id", chat)
                else:
                    task_id = int(msg)
                    query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                    try:
                        task = query.one()
                    except sqlalchemy.orm.exc.NoResultFound:
                        self.api.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                        return
                    task.status = 'TODO'
                    db.session.commit()
                    self.api.send_message("*TODO* task [[{}]] {}".format(task.id, task.name), chat)

            elif command == '/doing':
                if not msg.isdigit():
                    self.api.send_message("You must inform the task id", chat)
                else:
                    task_id = int(msg)
                    query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                    try:
                        task = query.one()
                    except sqlalchemy.orm.exc.NoResultFound:
                        self.api.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                        return
                    task.status = 'DOING'
                    db.session.commit()
                    self.api.send_message("*DOING* task [[{}]] {}".format(task.id, task.name), chat)

            elif command == '/done':
                if not msg.isdigit():
                    self.api.send_message("You must inform the task id", chat)
                else:
                    task_id = int(msg)
                    query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                    try:
                        task = query.one()
                    except sqlalchemy.orm.exc.NoResultFound:
                        self.api.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                        return
                    task.status = 'DONE'
                    db.session.commit()
                    self.api.send_message("*DONE* task [[{}]] {}".format(task.id, task.name), chat)

            elif command == '/list':
                task_list = ''

                task_list += '\U0001F4CB Task List\n'
                query = db.session.query(Task).filter_by(parents='', chat=chat).order_by(Task.id)
                for task in query.all():
                    icon = '\U0001F195'
                    if task.status == 'DOING':
                        icon = '\U000023FA'
                    elif task.status == 'DONE':
                        icon = '\U00002611'

                    task_list += '[[{}]] {} {}\n'.format(task.id, icon, task.name)
                    task_list += deps_text(task, chat)

                self.api.send_message(task_list, chat)
                tasks_by_status = ''

                tasks_by_status += '\U0001F4DD _Status_\n'
                query = db.session.query(Task).filter_by(status='TODO', chat=chat).order_by(Task.id)
                tasks_by_status += '\n\U0001F195 *TODO*\n'
                for task in query.all():
                    tasks_by_status += '[[{}]] {}\n'.format(task.id, task.name)
                query = db.session.query(Task).filter_by(status='DOING', chat=chat).order_by(Task.id)
                tasks_by_status += '\n\U000023FA *DOING*\n'
                for task in query.all():
                    tasks_by_status += '[[{}]] {}\n'.format(task.id, task.name)
                query = db.session.query(Task).filter_by(status='DONE', chat=chat).order_by(Task.id)
                tasks_by_status += '\n\U00002611 *DONE*\n'
                for task in query.all():
                    tasks_by_status += '[[{}]] {}\n'.format(task.id, task.name)

                self.api.send_message(tasks_by_status, chat)
            elif command == '/dependson':
                text = ''
                if msg != '':
                    if len(msg.split(' ', 1)) > 1:
                        text = msg.split(' ', 1)[1]
                    msg = msg.split(' ', 1)[0]

                if not msg.isdigit():
                    self.api.send_message("You must inform the task id", chat)
                else:
                    task_id = int(msg)
                    query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                    try:
                        task = query.one()
                    except sqlalchemy.orm.exc.NoResultFound:
                        self.api.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                        return

                    if text == '':
                        for i in task.dependencies.split(',')[:-1]:
                            i = int(i)
                            query = db.session.query(Task).filter_by(id=i, chat=chat)
                            task_dep = query.one()
                            task_dep.parents = task_dep.parents.replace('{},'.format(task.id), '')

                        task.dependencies = ''
                        self.api.send_message("Dependencies removed from task {}".format(task_id), chat)
                    else:
                        for depid in text.split(' '):
                            if not depid.isdigit():
                                self.api.send_message("All dependencies ids must be numeric, and not {}".format(depid), chat)
                            else:
                                depid = int(depid)
                                query = db.session.query(Task).filter_by(id=depid, chat=chat)
                                try:
                                    taskdep = query.one()
                                    taskdep.parents += str(task.id) + ','
                                except sqlalchemy.orm.exc.NoResultFound:
                                    self.api.send_message("_404_ Task {} not found x.x".format(depid), chat)
                                    continue

                                deplist = task.dependencies.split(',')
                                if str(depid) not in deplist:
                                    task.dependencies += str(depid) + ','

                    db.session.commit()
                    self.api.send_message("Task {} dependencies up to date".format(task_id), chat)
            elif command == '/priority':
                text = ''
                if msg != '':
                    if len(msg.split(' ', 1)) > 1:
                        text = msg.split(' ', 1)[1]
                    msg = msg.split(' ', 1)[0]

                if not msg.isdigit():
                    self.api.send_message("You must inform the task id", chat)
                else:
                    task_id = int(msg)
                    query = db.session.query(Task).filter_by(id=task_id, chat=chat)
                    try:
                        task = query.one()
                    except sqlalchemy.orm.exc.NoResultFound:
                        self.api.send_message("_404_ Task {} not found x.x".format(task_id), chat)
                        return

                    if text == '':
                        task.priority = ''
                        self.api.send_message("_Cleared_ all priorities from task {}".format(task_id), chat)
                    else:
                        if text.lower() not in ['high', 'medium', 'low']:
                            self.api.send_message("The priority *must be* one of the following: high, medium, low", chat)
                        else:
                            task.priority = text.lower()
                            self.api.send_message("*Task {}* priority has priority *{}*".format(task_id, text.lower()), chat)
                    db.session.commit()

            elif command == '/start':
                self.api.send_message("Welcome! Here is a list of things you can do.", chat)
                self.api.send_message(self.api.HELP, chat)
            elif command == '/help':
                self.api.send_message("Here is a list of things you can do.", chat)
                self.api.send_message(self.api.HELP, chat)
            else:
                self.api.send_message("I'm sorry dave. I'm afraid I can't do that.", chat)

def deps_text(task, chat, preceed=''):
    text = ''

    for i in range(len(task.dependencies.split(',')[:-1])):
        line = preceed
        query = db.session.query(Task).filter_by(id=int(task.dependencies.split(',')[:-1][i]), chat=chat)
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




def main():
    last_update_id = None
    api = Api()
    tasks_controller = TasksController(api)

    while True:
        print("Updates")
        updates = api.get_updates(last_update_id)

        if updates["result"]:
            last_update_id = api.get_last_update_id(updates) + 1
            tasks_controller.handle_updates(updates)

        time.sleep(0.5)


if __name__ == '__main__':
    main()
