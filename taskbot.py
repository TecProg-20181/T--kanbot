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
    @classmethod
    def get_token(cls):
        with open('token.txt') as token_file:
            token = token_file.read()
            return token

    @classmethod
    def get_url(cls, url):
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

    @classmethod
    def get_last_update_id(cls, updates):
        update_ids = []
        for update in updates["result"]:
            update_ids.append(int(update["update_id"]))

        return max(update_ids)

    def handle_updates(self, updates):
        controller = TasksController()

        for update in updates["result"]:
            if 'message' in update:
                message = update['message']
            elif 'edited_message' in update:
                message = update['edited_message']
            else:
                print ('Can\'t process! {}').format(update)
                return

            command = message["text"].split(" ", 1)[0]
            msg = ''
            if len(message["text"].split(" ", 1)) > 1:
                msg = message["text"].split(" ", 1)[1].strip()

            chat = message["chat"]["id"]

            print(command, msg, chat)

            if command == '/new':
                response = controller.new_task(msg, chat)
                self.send_message(response, chat)
            elif command == '/rename':
                response = controller.rename_task(msg, chat)
                self.send_message(response, chat)
            elif command == '/duplicate':
                response = controller.duplicate_task(msg, chat)
                self.send_message(response, chat)
            elif command == '/delete':
                response = controller.delete_task(msg, chat)
                self.send_message(response, chat)
            elif command == '/todo':
                response = controller.move_todo(msg, chat)
                self.send_message(response, chat)
            elif command == '/doing':
                response = controller.move_doing(msg, chat)
                self.send_message(response, chat)
            elif command == '/done':
                response = controller.move_done(msg, chat)
                self.send_message(response, chat)
            elif command == '/list':
                response = controller.list_tasks(msg, chat)
                self.send_message(response[0], chat)
                self.send_message(response[1], chat)
            elif command == '/dependson':
                response = controller.depends_on(msg, chat)
                self.send_message(response, chat)
            elif command == '/priority':
                response = controller.set_priority(msg, chat)
                self.send_message(response, chat)
            elif command == '/start':
                self.send_message("Welcome! Here is a list of things you can do.", chat)
                self.send_message(self.HELP, chat)
            elif command == '/help':
                self.send_message("Here is a list of things you can do.", chat)
                self.send_message(self.HELP, chat)
            else:
                self.send_message("I'm sorry dave. I'm afraid I can't do that.", chat)


class TasksController:

    @classmethod
    def new_task(cls, msg, chat):
        task = Task(chat=chat, name=msg, status='TODO', dependencies='', parents='', priority='')
        db.session.add(task)
        db.session.commit()
        return "New task *TODO* [[{}]] {}".format(task.id, task.name)

    @classmethod
    def rename_task(cls, msg, chat):
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
    def duplicate_task(cls, msg, chat):
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
                         duedate=task.duedate)
            db.session.add(dtask)

            for dependency in task.dependencies.split(',')[:-1]:
                query = db.session.query(Task).filter_by(id=int(dependency), chat=chat)
                dependency = query.one()
                dependency.parents += '{},'.format(dtask.id)

            db.session.commit()
            return "New task *TODO* [[{}]] {}".format(dtask.id, dtask.name)

    @classmethod
    def delete_task(cls, msg, chat):
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

    @classmethod
    def move_todo(cls, msg, chat):
        if not msg.isdigit():
            return "You must inform the task id"
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)
            task.status = 'TODO'
            db.session.commit()
            return "*TODO* task [[{}]] {}".format(task.id, task.name)

    @classmethod
    def move_doing(cls, msg, chat):
        if not msg.isdigit():
            return "You must inform the task id"
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)
            task.status = 'DOING'
            db.session.commit()
            return "*DOING* task [[{}]] {}".format(task.id, task.name)

    @classmethod
    def move_done(cls, msg, chat):
        if not msg.isdigit():
            return "You must inform the task id"
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                return "_404_ Task {} not found x.x".format(task_id)
            task.status = 'DONE'
            db.session.commit()
            return "*DONE* task [[{}]] {}".format(task.id, task.name)

    @classmethod
    def list_tasks(cls, msg, chat):
        task_list = ''
        tasks_by_status = ''
        list_messages = []

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

        list_messages.append(task_list)

        tasks_by_status += '\U0001F4DD _Status_\n'
        query = db.session.query(Task).filter_by(status='TODO', chat=chat).order_by(Task.id)
        tasks_by_status += '\n\U0001F195 *TODO*\n'
        for task in query.all():
            tasks_by_status += '[[{}]] {} - {}\n'.format(task.id, task.name, task.priority)
        query = db.session.query(Task).filter_by(status='DOING', chat=chat).order_by(Task.id)
        tasks_by_status += '\n\U000023FA *DOING*\n'
        for task in query.all():
            tasks_by_status += '[[{}]] {} - {}\n'.format(task.id, task.name, task.priority)
        query = db.session.query(Task).filter_by(status='DONE', chat=chat).order_by(Task.id)
        tasks_by_status += '\n\U00002611 *DONE*\n'
        for task in query.all():
            tasks_by_status += '[[{}]] {} - {}\n'.format(task.id, task.name, task.priority)

        list_messages.append(tasks_by_status)
        return list_messages

    @classmethod
    def depends_on(cls, msg, chat):
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
    def set_priority(cls, msg, chat):
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




def main():
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
