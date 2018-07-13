activate_this = "/env/bin/activate_this.py"
execfile(activate_this, dict(__file__=activate_this))

import sys
if hasattr(sys, 'real_prefix'):
        print >> sys.stderr, 'sys.real_prefix = %s' % repr(sys.real_prefix)
        print >> sys.stderr, 'sys.prefix = %s' % repr(sys.prefix)
else:
        print >> sys.stderr, 'no virtual env'



from flask import Flask, request, Response, json, make_response, jsonify
import hmac
import hashlib
import base64
from twitter import TwitterConnection, Messenger
import sys
sys.stdout = open('/output.logs', 'w')
app = Flask(__name__)

print "SYS PREFIX", sys.prefix
print "SYS PATH", sys.path
consumer_secret = ""
consumer_key = ""
access_token = ""
access_token_secret = ""

msg = Messenger(consumer_key, consumer_secret, access_token, access_token_secret)


@app.route("/")
def hello():
    return "Hello World!"


@app.route('/webhook', methods=["GET"])
def validation():
    print "validation"
    try:
        crc = request.args['crc_token']
        crc = str(crc)
        print "got crc", crc
        validation = hmac.new(
            key=consumer_secret,
            msg=crc,
            digestmod = hashlib.sha256
        )
        signature = base64.b64encode(validation.digest())
        print signature

        data = {"response_token": "sha256=" + signature}

        return jsonify(data)
    except:
        return "HELLO WORLD"


@app.route('/webhook', methods=["POST"])
def handle_request():
    try:
        tw_signature = request.headers['X-Twitter-Webhooks-Signature']
        tw_signature = tw_signature.replace('sha256=', '')
        validation = hmac.new(
            key=consumer_secret,
            msg=request.data,
            digestmod = hashlib.sha256
        )
        signature = base64.b64encode(validation.digest())
        if (type(signature) != str):
            signature = str(signature)
        if (type(tw_signature) != str):
            tw_signature = str(tw_signature)

        #comapre hashes to check validation
        valid = hmac.compare_digest(signature, tw_signature)
        print "valid", valid

        if valid == True:
            message = request.json["direct_message_events"]
            msg.run(message)

    except Exception as e:
        return "HELLO WORLD"


if __name__ == "__main__":
    app.run(debug=True)
