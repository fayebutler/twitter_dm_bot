from __future__ import print_function
from config import config
from flask import Flask, request, Response, json, make_response, jsonify
import hmac
import hashlib
import base64
from twitter import TwitterConnection, Messenger
import sys
app = Flask(__name__)


consumer_secret = config["consumer_secret"]
consumer_key = config["consumer_key"]
access_token = config["access_token"]
access_token_secret = config["access_token_secret"]

msg = Messenger(consumer_key, consumer_secret, access_token, access_token_secret)


@app.route("/")
def hello():
    print('hello world', file=sys.stderr)
    return "Hello World!"


@app.route('/webhook', methods=["GET"])
def validation():
    #print "validation"
    print('webhook url called', file=sys.stderr)
    try:
        crc = request.args['crc_token']
        crc = str(crc)
        #print "got crc", crc
        print('crc got:' + crc, file=sys.stderr)
        validation = hmac.new(
            key=consumer_secret,
            msg=crc,
            digestmod = hashlib.sha256
        )
        signature = base64.b64encode(validation.digest())
        #print signature

        data = {"response_token": "sha256=" + signature}

        #return jsonify(data)
        return json.dumps(data)
    except:
        return "HELLO WORLD"


@app.route('/webhook', methods=["POST"])
def handle_request():
    try:
        tw_signature = request.headers['X-Twitter-Webhooks-Signature']
        tw_signature = tw_signature.replace('sha256=', '')
        #tw_signature = base64.b64encode(tw_signature)

        validation = hmac.new(
            key=consumer_secret,
            msg=request.data,
            digestmod = hashlib.sha256
        )
        signature = validation.digest()
        signature = base64.b64encode(signature)

        if (type(signature) != str):
            signature = str(signature)

        if (type(tw_signature) != str):
            tw_signature = str(tw_signature)

        #print("signature: " + signature, file=sys.stderr)
        #print("twitter: " + tw_signature, file=sys.stderr)

        #pythonanywhere only has python2.7.6 and compare_digest is only available from python 2.7.10
        #instead just do a normal string comparison -- not as safe as doesn't stop timing attacks
        valid = False
        try:
            valid = hmac.compare_digest(signature, tw_signature)
        except AttributeError as e:
            valid = (signature == tw_signature)
        #print(valid, file=sys.stderr)

        if valid == True:
            #print('validated message from twitter', file=sys.stderr)
            message = request.json["direct_message_events"]
            msg.run(message)

    except Exception as e:
        return "HELLO WORLD"


# if __name__ == "__main__":
#     app.run(debug=True)
