#!/usr/bin/env python2.7
import mastodon,sys,time,os,json

class AutoResponder():
    def __init__(self,config):
        self.config = config
    def checkForFollows(self):
        try:
            follows = self.config.api.follow_requests()
        except mastodon.MastodonUnauthorizedError as e:
            sys.stderr.write('API error; unauthorized action.\n%s\n'%str(e))
            sys.exit()
        except mastodon.MastodonRatelimitError:
            sys.stderr.write('Rate-limited by server.  You may be running too many clients.\n')
            return
        for follow in follows:
            if follow['id'] not in self.config.follow_requests_seen:
                self.config.follow_requests_seen += [follow['id']]
                self.config.api.status_post(status=self.config.response%('@'+follow['acct']),visibility='direct')

    def run(self):
        timer = 0
        while True:
            timer+=1
            self.checkForFollows()
            time.sleep(60)
            if timer>119:
                self.config.writeConfig()
                timer = 0

class config():
    def __init__(self):
        self.api = None
        self.response = ''
        self.client_id = ''
        self.client_secret = ''
        self.auth_key = ''
        self.base_url = ''
        self.follow_requests_seen = []

    def readConfig(self):
        try:
            config = open(os.path.expanduser("~/.fedifollowautoresponder"))
            parsed_config = json.load(config)
        except:
            self.buildConfig()
            return
        self.response = parsed_config['response']
        self.client_id = parsed_config['client_id']
        self.client_secret = parsed_config['client_secret']
        self.auth_key = parsed_config['auth_key']
        self.base_url = parsed_config['base_url']
        try:
            self.follow_requests_seen = parsed_config['follow_requests_seen']
        except KeyError:
            self.follow_requests_seen = []
        self.api = mastodon.Mastodon(client_id=self.client_id,client_secret=self.client_secret,api_base_url=self.base_url,access_token=self.auth_key)
        try:
            self.api.follow_requests()
        except Exception as e:
            print 'Authentication error.  Please try logging in again.'
            self.auth_key = ''
            self.buildConfig()
    
    def writeConfig(self):
        try:
            config = open(os.path.expanduser("~/.fedifollowautoresponder"),'w')
        except IOError:
            sys.stderr.write('Could not write config to ~/.fedifollowautoresponder\n')
            sys.exit()
        os.chmod(os.path.expanduser("~/.fedifollowautoresponder"),0o600)
        json.dump({'response':self.response,'client_id':self.client_id,'client_secret':self.client_secret,'auth_key':self.auth_key,'base_url':self.base_url,'follow_requests_seen':self.follow_requests_seen},config)
        config.close()

    def buildConfig(self):
        while self.base_url == '':
            self.base_url = raw_input('Mastodon API-compatible instance (https://mastodon.social for example): ')
            try:
                (self.client_id,self.client_secret) = mastodon.Mastodon.create_app('Fediverse follow request autoresponder 201902202200',scopes=['read:follows','write:statuses'],api_base_url=self.base_url)
            except Exception as e:
                self.base_url = ''
                print 'Failed to connect to instance.  Please double check that it is spelled correctly.'
                print str(e)
                print '\n'
        self.api = mastodon.Mastodon(client_id=self.client_id,client_secret=self.client_secret,api_base_url=self.base_url)
        while self.auth_key == '':
            self.auth_key = raw_input('Please go to this URL to authorize the app to access your account, and copy and paste the code it gives below.\n%s\nCode: ' % self.api.auth_request_url(client_id=self.client_id,scopes=['read:follows','write:statuses']))
            try:
                self.auth_key = self.api.log_in(code=self.auth_key,scopes=['read:follows','write:statuses'])
            except Exception as e:
                self.auth_key = ''
                print 'Unable to log in.'
                print str(e)
                print '\n'
        response = raw_input('Current response message: %s\nEnter new message.  %%s will be replaced with the username of the requestor.  If you need a %%, then use %%%%.  Blank to keep the current message.\n'%self.response)
        if response.strip() != '':
            self.response = response
        self.writeConfig()
        print 'Configuration complete and successfully written to disk.'


if __name__=='__main__':
    config = config()
    config.readConfig()
    responder = AutoResponder(config)
    responder.run()
