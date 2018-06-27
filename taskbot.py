#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This code controls a telegram bot. This bot is a kanban."""
import time

from taskbot_api import Api
     
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
