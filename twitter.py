from config import config
import oauth2
import urllib
import sched, time
import json
import os
import sys

import requests
from requests_oauthlib import OAuth1

s = sched.scheduler(time.time, time.sleep)

consumer_secret = config["consumer_secret"]
consumer_key = config["consumer_key"]
access_token = config["access_token"]
access_token_secret = config["access_token_secret"]

webhook_id = config['webhook_id']

#webhook_url = urllib.quote_plus(config['webhook_url'])
webhook_url = config['webhook_url']


class TwitterConnection(object):
    """
    Class that connects to twitter through get/post HTTP requests.
    Sets up authorization and returns decoded JSON responses
    """
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):
        """
        Initilaise OAuth authorisation
        """
        self.oauth = OAuth1(consumer_key,
          client_secret=consumer_secret,
          resource_owner_key=access_token,
          resource_owner_secret=access_token_secret)


    def get_webhooks(self):
        """
        Get webhook config
        """
        response = requests.get(url="https://api.twitter.com/1.1/account_activity/all/webhooks.json", auth=self.oauth)
        print response.json()

    def delete_webhook(self):
        """
        Delete a webhook
        """
        response = requests.delete(url="https://api.twitter.com/1.1/account_activity/all/dev/webhooks/" + webhook_id + ".json", auth=self.oauth)
        if response.status_code == 204:
            print "deleted"
        else:
            print response.json()

    def set_up_webhook(self):
        """
        Set up a web hook for account activity
        """
        response = requests.post(url="https://api.twitter.com/1.1/account_activity/all/dev/webhooks.json",  headers={"content-type" : "application/x-www-form-urlencoded"}, data={"url" : webhook_url}, auth=self.oauth)
        print response.json()

    def challenge_webhook(self):
        """
        Send CRC check to webhook
        """
        response = requests.put(url="https://api.twitter.com/1.1/account_activity/all/dev/webhooks/" + webhook_id + ".json", auth=self.oauth)
        if response.status_code == 204:
            print "webhook valid"
        else:
            print response.json()

    def subscribe_to_webhook(self):
        """
        Subscribe user to webhook using webhook id
        """
        response = requests.post(url="https://api.twitter.com/1.1/account_activity/all/dev/subscriptions.json", auth=self.oauth)
        print response
        if response.status_code == 204:
            print "subscription success"
        else:
            print response.status_code
            print response.json()

    def count_subscriptions(self):
        """
        Count all the subscriptions to the webhook
        """
        response = requests.get(url="https://api.twitter.com/1.1/account_activity/subscriptions/count", auth=self.oauth)
        print response.json()

    def list_subscriptions(self):
        """
        List all the subscriptions to the webhook
        """
        response = requests.get(url="https://api.twitter.com/1.1/account_activity/all/dev/subscriptions/list", auth=self.oauth)
        print response.json()

    def check_subscription(self):
        """
        Check subscribed to webhook
        """
        response = requests.get(url="https://api.twitter.com/1.1/account_activity/all/dev/subscriptions", auth=self.oauth)
        if response.status_code == 204:
            print "subscribed"
        else:
            print response.json()

    def delete_subscription(self):
        """
        Delete subscription
        """
        response = requests.delete(url="https://api.twitter.com/1.1/account_activity/all/:env_name/subscriptions", auth=self.oauth)
        if response.status_code == 204:
            print "deleted"
        else:
            print response.json()

    def get_messages(self):
        """
        Return a json decoded response
        List of dictionaries, each dictionary is a direct message
        """
        direct_messages = requests.get(url='https://api.twitter.com/1.1/direct_messages/events/list.json', auth=self.oauth)
        try:
            direct_messages = direct_messages.json()['events']
            print "TOP MESSAGE", direct_messages[0]
            return direct_messages
        except KeyError:
            print direct_messages.json()
            sys.exit(1)

    def upload_media(self, file_name, media_type, media_category):
        """
        Chunk upload media to twitter and return the media ID once processing is successful
        """
        total_bytes = os.path.getsize(file_name)
        print "INIT"


        request_data = {
          'command': 'INIT',
          'media_type': 'video/mp4',
          'total_bytes': total_bytes,
          'media_category': 'dm_video'
        }
        #first init
        init_req = requests.post(url='https://upload.twitter.com/1.1/media/upload.json', data=request_data, auth=self.oauth)
        print init_req
        print init_req.json()
        media_id = init_req.json()['media_id']


        #then we chunk upload
        segment_id = 0
        bytes_sent = 0
        file = open(file_name, 'rb')

        while bytes_sent < total_bytes:
            chunk = file.read(1000000)
            print 'APPEND'

            request_data = {
            'command': 'APPEND',
            'media_id': media_id,
            'segment_index': segment_id
            }

            files = {
            'media':chunk
            }

            append_req = requests.post(url='https://upload.twitter.com/1.1/media/upload.json', data=request_data, files=files, auth=self.oauth)

            print append_req
            print(append_req.status_code)
            print(append_req.text)

            segment_id += 1
            bytes_sent = file.tell()

            print '%s of %s bytes uploaded' % (str(bytes_sent), str(total_bytes))

        print 'Upload chunks complete.'


        print "FINAL"

        request_data = {
          'command': 'FINALIZE',
          'media_id': media_id
        }

        final_req = requests.post(url='https://upload.twitter.com/1.1/media/upload.json', data=request_data, auth=self.oauth)

        print final_req.json()

        processing_info = final_req.json().get('processing_info', None)

        #check video processing
        check = self.check_status(processing_info, media_id)
        return check

    def check_status(self, processing_info, media_id):
        '''
        Checks video processing status
        '''
        if processing_info is None:
          print " no info"
          return

        state = processing_info['state']

        print('Media processing status is %s ' % state)

        if state == u'succeeded':
          print "succeeded", media_id
          return media_id

        if state == u'failed':
          print "failed"
          sys.exit(0)

        check_after_secs = processing_info['check_after_secs']

        print('Checking after %s seconds' % str(check_after_secs))
        time.sleep(check_after_secs)

        print('STATUS')

        request_params = {
          'command': 'STATUS',
          'media_id': media_id
        }

        req = requests.get(url='https://upload.twitter.com/1.1/media/upload.json', params=request_params, auth=self.oauth)

        processing_info = req.json().get('processing_info', None)
        return self.check_status(processing_info, media_id)

    def response(self, message_data, recipient_id):
        """
        Sends a direct message using message data argument
        """
        request_params = {
                "event" : {
                            "type": "message_create",
                            "message_create": {
                                                "target": { "recipient_id": recipient_id},
                                                "message_data": message_data
                        }
            }
        }
        req = requests.post(url='https://api.twitter.com/1.1/direct_messages/events/new.json', headers={"content-type" : "application/json"}, data=json.dumps(request_params), auth=self.oauth)
        print req
        print req.json()

class Messenger(object):

    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):
        self.prev_messages = []
        self.twitter = TwitterConnection(consumer_key, consumer_secret, access_token, access_token_secret)
        self.my_sender_id = "811593743858073600"
        self.conversations = []

    def run(self, new_messages):
        """
        Run this show!
        """
        #get the messages from twitter
        #messages = self.twitter.get_messages()
        #if not self.prev_messages:
        #    print "not got a previous Message"
        #    self.prev_messages = messages
        #    return
        #filter what ones are new
        #new_messages = self.get_new_messages(messages)
        #print "The new msg", new_messages
        #sort out messages into new and old
        new_convo_messages = []
        old_convo_messages = []
        for message in new_messages:
            print "checking message"
            #ignore the messages I've sent
            if self.check_sent_by_me(message) == False:
                print "sent by someone else!"
                #sent by someone else - A reply
                if self.check_in_convo(message) == False:
                    print "new convo!"
                    #start new
                    new_convo_messages.append(message)
                else:
                    #continue old
                    old_convo_messages.append(message)

        for message in new_convo_messages:
            print "start the convo"
            self.start_conversation(message)

        for message in old_convo_messages:
            convo = self.get_conversation(message)
            self.continue_conversation(message, convo)

        self.prev_messages = messages

        #s.enter(60, 1, self.run, ())

    def get_new_messages(self, messages):
        """
        Returns a list of dictionaries that are in messsages but not in prev_messages
        """
        diff = [i for i in messages if i not in self.prev_messages]
        return diff

    def check_sent_by_me(self, message):
        """
        Check if the message was sent by me or someone else
        """
        if message['message_create']['sender_id'] == self.my_sender_id:
            return True
        else:
            return False

    def check_in_convo(self, message):
        """
        Check If I've already started a conversation with this ID
        """
        print "checking convo", self.conversations
        for convo in self.conversations:
            if message['message_create']['sender_id'] == convo['sender_id']:
                return True
        return False

    def start_conversation(self, message):
        """
        Start the conversation
        """
        print "start /cont conversation func"
        convo = {"sender_id" : message['message_create']['sender_id'], "position" : 0}
        self.conversations.append(convo)
        self.continue_conversation(message, convo)

    def get_conversation(self, message):
        """
        Return the conversation dictionary for this sender ID
        """
        result = [convo for convo in self.conversations if convo["sender_id"] == message['message_create']['sender_id']]
        print "get convo result",result
        return result[0]

    def continue_conversation(self, message, convo):
        """
        Continue conversations
        """
        print "continue conversation func"
        #start of conversations
        if convo['position'] == 0:
            print " MOVIE REC?"
            #Would you like a movie recommendation?
            reply = {"text" : "Would you like a movie recommendation?", "quick_reply" : {"type" : "options", "options" : [{"label" : "Yes"}, {"label" : "No"}]}}
            self.twitter.response(reply, message['message_create']['sender_id'])
            convo['position'] = 1
        elif convo['position'] == 1:
            #What genre do you like?
            if message['message_create']['message_data']['text'] == "Yes":
                reply = {"text" : "What genre do you like?", "quick_reply" : {"type" : "options", "options" : [{"label" : "Comedy"}, {"label" : "Action"}]}}
                self.twitter.response(reply, message['message_create']['sender_id'])
                convo['position'] = 2
            elif message['message_create']['message_data']['text'] == "No":
                reply = {"text" : "No worries, come back soon"}
                self.twitter.response(reply, message['message_create']['sender_id'])
                convo['position'] = 0
            else:
                reply = {"text" : "Sorry didn't get that. Would you like a movie recommendation?", "quick_reply" : {"type" : "options", "options" : [{"label" : "Yes"}, {"label" : "No"}]}}
                self.twitter.response(reply, message['message_create']['sender_id'])
                convo['position'] = 1
        elif convo['position'] == 2:
            #Heres a movie
            if message['message_create']['message_data']['text'] == "Comedy":
                media_id = self.twitter.upload_media('assets/BossBaby_vid.mp4', 'video/mp4', 'dm_video')
                reply = {"text" : "Boss Baby is a fun comedy! http://www.imdb.com/title/tt3874544/. Thanks!", "attachment" : {"type" : "media", "media" : { "id" : media_id}}}
                self.twitter.response(reply, message['message_create']['sender_id'])
                convo['position'] = 0
            elif message['message_create']['message_data']['text'] == "Action":
                media_id = self.twitter.upload_media('assets/Apes_vid.mp4', 'video/mp4', 'dm_video')
                reply = {"text" : "War for the Planet of the Apes is an action! http://www.imdb.com/title/tt3450958/. Thanks!", "attachment" : {"type" : "media", "media" : { "id" : media_id}}}
                self.twitter.response(reply, message['message_create']['sender_id'])
                convo['position'] = 0
            else:
                reply = {"text" : "Sorry what genre was that?", "quick_reply" : {"type" : "options", "options" : [{"label" : "Comedy"}, {"label" : "Action"}]}}
                self.twitter.response(reply, message['message_create']['sender_id'])
                convo['position'] = 2


#msg = Messenger(consumer_key, consumer_secret, access_token, access_token_secret)
#msg.run()
#s.enter(60, 1, msg.run, ())
#s.run()

#twitter = TwitterConnection(consumer_key, consumer_secret, access_token, access_token_secret)
#twitter.delete_webhook()
#twitter.set_up_webhook()
#twitter.subscribe_to_webhook()
#twitter.list_subscriptions()
#twitter.get_webhooks()
#twitter.challenge_webhook()
#twitter.delete_webhook()
