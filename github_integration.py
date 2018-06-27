import json
import urllib
import requests

from contracts import contract

class GithubIntegration:
    REPOSITORY_OWNER='TecProg-20181'
    REPOSITORY_NAME='T--kanbot'

    USERNAME = ''
    PASSWORD = ''

    @contract(returns='list')
    def user_login(self):
        """This function gets the bot login."""
        with open('login.txt') as login_file:
            login = login_file.read().split('\n')
            return login

    @contract(msg='str', body='str', returns='str')
    def create_issue(self, msg, body=None):
        """This function creates an issue on github."""
        login = self.user_login()

        self.USERNAME = login[0]
        self.PASSWORD = login[1]

        url = 'https://api.github.com/repos/%s/%s/issues' % (self.REPOSITORY_OWNER, self.REPOSITORY_NAME)
        
        session = requests.Session()

        session.auth = (self.USERNAME, self.PASSWORD)

        issue = {'title': msg,
                'body': body}

        payload = json.dumps(issue)
        response = session.post(url, payload)

        if response.status_code == 201:
            return 'Successfully created Issue {0:s}'.format(msg)
        else:
            print ('Response:', response.content)
            return 'Could not create Issue {0:s}'.format(msg)