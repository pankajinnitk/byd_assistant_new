#!/usr/bin/env python
import http.client, base64

import json
import os
import requests

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    #print("Request:")
    #print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    print("Response:")
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):
    session = requests.Session()

    baseurl = "https://my316075.sapbydesign.com/sap/byd/odata/cust/v1/purchasing/"
    session.headers.update({'authorization' : "Basic " + base64.encodestring(('%s:%s' % ("odata_demo", "Welcome01")).encode()).decode().replace('\n', '')})
    session.headers.update({'x-csrf-token' : 'fetch'})
    print(session)
    res = session.get(baseurl, data = {'user' :'odata_demo','password' : 'Welcome01'}, proxies = "")
    print(res)
    session.headers.update({'x-csrf-token' : res.headers.get("x-csrf-token")})

    method, query = makeQuery(req, baseurl, session)
    qry_url = baseurl + query
    print(qry_url)
        
    if method == 'get':
        result = session.get(qry_url)
    else:
        result = session.post(qry_url)
    
    data = json.loads(result.text)
    print("data")
    print(data)
    res = makeWebhookResult(data, req)
    return res	

def makeQuery(req, baseurl, session):
    result = req.get("result")
    parameters = result.get("parameters")
    poid = parameters.get("id")
    status = parameters.get("status")
    action = parameters.get("po-action")
	
    intent = result.get("action")    
    if intent == "find-status" or intent == "po-details":
        return "get" , "PurchaseOrderCollection/?%24filter=PurchaseOrderID%20eq%20'" + poid + "'&%24format=json" 
    elif intent == "find-count":
        return "get" , "PurchaseOrderCollection/$count?%24filter=PurchaseOrderLifeCycleStatusCodeText%20eq%20'" + status + "'"
    elif intent == "po-action":
        qry_url = baseurl + "PurchaseOrderCollection/?%24filter=PurchaseOrderID%20eq%20'" + poid + "'&%24format=json" 
        print(qry_url)
        res = session.get(qry_url)
        result = res.text
        print(result)
        data = json.loads(result)
        node_id = data.get('d').get('results')[0].get('ObjectID')
        return "post" , action + "?" + "ObjectID='" + node_id +"'" + "'&%24format=json"
    else:
        return {}
	
def makeWebhookResult(data, req):
    messages = []
    intent = req.get("result").get("action")    
    if intent == "find-status":		
        value = data.get('d').get('results')
        node_id = value[0].get('ObjectID')
        print(node_id)
        print("json.results: ")
        print(json.dumps(value, indent=4))
        speech = "The status of Purchase Order ID " + str(value[0].get('PurchaseOrderID')) + \
             	 " is " + value[0].get('PurchaseOrderLifeCycleStatusCodeText')
    
    elif intent == "po-details":		
        value = data.get('d').get('results')
        node_id = value[0].get('ObjectID')
        print(node_id)
        print("json.results: ")
        print(json.dumps(value, indent=4))
        speech = "Here are the details"
        messages.append( {
                "type": "list_card",
                "platform": "google",
                "title": "Details of PO " + value[0].get('PurchaseOrderID'),
                "items": [
                {
                    "optionInfo": {
                    "key": "Supplier",
                    "synonyms": ["Seller"]
                    },
                    "title": "Supplier",
                    "description": value[0].get('SellerPartyID')
                },
                {
                    "optionInfo": {
                    "key": "amount",
                    "synonyms": ["Value"]
                    },
                    "title": "Net Value",
                    "description": value[0].get('TotalNetAmount') + value[0].get('CurrencyCodeText')
                },
                {
                    "optionInfo": {
                    "key": "Buyer",
                    "synonyms": ["Company"]
                    },
                    "title": "Buyer Party",
                    "description": value[0].get('BuyerPartyID')
                }
                ]
            } )
        messages.append( {
              "type": 0,
              "speech": "Supplier of PO " + value[0].get('PurchaseOrderID') + "is" +  value[0].get('SellerPartyID') + "." + \
                         "Total Net Value is " + value[0].get('TotalNetAmount') + value[0].get('CurrencyCodeText') + "." + \
                         "Buyer Party is " + value[0].get('BuyerPartyID') + "."
            } )
            
    elif intent == "find-count":        
        if int(data) > 1:
            speech = "There are " + str(data) + " purchase orders in the system with " + \
                      req.get("result").get("parameters").get("status") + " status"
        elif int(data) == 1:
            speech = "There is " + str(data) + " purchase order in the system with " + \
                      req.get("result").get("parameters").get("status") + " status"
        else:
            speech = "There are no purchase orders in the system with " + \
                      req.get("result").get("parameters").get("status") + " status"
    elif intent == "po-action":
        value = data.get('d').get('results')
        node_id = value.get('ObjectID')
        speech = "The status of Purchase Order ID " + str(value.get('PurchaseOrderID')) + \
             	 " is " + value.get('PurchaseOrderLifeCycleStatusCodeText')
    else:
        speech = "Sorry, I did not understand you! Please try again"
	
    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        "messages": [ messages ],
        #"contextOut": node_id,
        "source": "bydassistant"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

app.run(debug=False, port=port, host='0.0.0.0')
