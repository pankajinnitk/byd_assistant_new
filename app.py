#!/usr/bin/env python
import base64

import json
import os
import requests
from datetime import datetime

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    result = req.get("result")
    action_name = result.get("action")
    print("action:", action_name)
    if action_name == 'record-time':
        parameters = result.get("parameters")
        res = record_the_time(req, parameters)
        res_final = json.dumps(res, indent=4)
        r = make_response(res_final)
        r.headers['Content-Type'] = 'application/json'
        return r
    else:
        res = processRequest(req)
        res = json.dumps(res, indent=4)
        print("Response:")
        print(res)
        r = make_response(res)
        r.headers['Content-Type'] = 'application/json'
        return r

def record_the_time(req, parameters):
    session = requests.Session()
    # setup header, auth, token for POST
    baseurl = 'https://my316075.sapbydesign.com/sap/byd/odata/cust/v1/timerecording/'
    # baseurl = 'https://my316075.sapbydesign.com/sap/byd/odata/cust/v1/timerecording/EmployeeTime1Collection/'
    session.headers.update({'authorization' : "Basic " + base64.encodestring(('%s:%s' % ("odata_demo", "Welcome01")).encode()).decode().replace('\n', '')})
    session.headers.update({'x-csrf-token' : 'fetch'})
    res = session.get(baseurl, data = {'user' :'odata_demo','password' : 'Welcome01'}, proxies = "")
    session.headers.update({'x-csrf-token' : res.headers.get("x-csrf-token")})

    # build the payload (dictionary object) to be sent to POST
    base_url_new = baseurl + 'EmployeeTime1Collection/'
    start_date = parameters.get('date')
    duration = parameters.get('duration')
    duration_formatted = "PT{}H0M".format(duration.get('amount')) #if duration is not None else "PT1H0M"
    start_date_formatted = datetime.strptime(start_date, "%Y-%m-%d").isoformat()
    
    payload_dict = {
        "EmployeeTimeAgreementItemUUID":"00000000-0001-1DEF-BAD7-DAE780B5CCCA",
        "EmployeeTimeItem":[{
            "ProductID":"S200101",
            "ProjectElementID":"CPSO49-1",
            "EndDate": start_date_formatted,
            "StartDate": start_date_formatted,
            "Duration": duration_formatted
        }]
    }

    payload_str = json.dumps(payload_dict)
    payload_json = json.loads(payload_str)
    result = session.post(base_url_new, json=payload_json)
    if result.reason == 'Created':
        res = makeWebhookResult(None, req)
    else:
        res = makeWebhookResult(None, req)
    return res    
    
def processRequest(req):
    session = requests.Session()

    baseurl = "https://my316075.sapbydesign.com/sap/byd/odata/cust/v1/purchasing/"
    session.headers.update({'authorization' : "Basic " + base64.encodestring(('%s:%s' % ("odata_demo", "Welcome01")).encode()).decode().replace('\n', '')})
    session.headers.update({'x-csrf-token' : 'fetch'})
    print(session)
    res = session.get(baseurl, data = {'user' :'odata_demo','password' : 'Welcome01'}, proxies = "")
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
    action = parameters.get("po-action")[0]    
	
    intent = result.get("action")    
    if intent == "find-status" or intent == "get-details":
        return "get" , "PurchaseOrderCollection/?%24filter=PurchaseOrderID%20eq%20'" + poid + "'&%24format=json" 
    elif intent == "find-count":
        return "get" , "PurchaseOrderCollection/$count?%24filter=PurchaseOrderLifeCycleStatusCodeText%20eq%20'" + status + "'"
    elif intent == "get-pos":
        dateduration = parameters.get("date-period").split("/")
        start_date = dateduration[0]
        end_date = dateduration[1]
        date = parameters.get("date")
        if date:
            return "get" , "PurchaseOrderCollection/$%24format=json&%24filter=CreationDateTime%20ge%20datetimeoffset'" + date + "'"
        else:
            return "get" , "PurchaseOrderCollection/?%24format=json&%24filter=CreationDateTime%20ge%20datetimeoffset'" + \
            start_date + "T00%3A00%3A00Z'%20and%20CreationDateTime%20le%20datetimeoffset'" + end_date + "T00%3A00%3A00Z'"
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
        messages.append( {
              "type": 0,
              "speech": speech
            } )

    elif intent == "get-details":		
        value = data.get('d').get('results')
        speech = "Here are the details"
        messages.append( {                                             
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
                    "description": "%.2f" % float(value[0].get('TotalNetAmount')) + " " + value[0].get('CurrencyCodeText')
                },
                {
                    "optionInfo": {
                    "key": "Buyer",
                    "synonyms": ["Company"]
                    },
                    "title": "Buyer Party",
                    "description": value[0].get('BuyerPartyID')
                }
                ],
                "title": "Details of PO " + value[0].get('PurchaseOrderID'),
                "platform": "google",
                "type": "list_card"
            } )
        messages.append( {
              "type": 0,
              "speech": "Supplier of PO " + value[0].get('PurchaseOrderID') + " is " +  value[0].get('SellerPartyID') + ". " + \
                         "Total Net Value is " + value[0].get('TotalNetAmount') + " " + value[0].get('CurrencyCodeText') + ". " + \
                         "Buyer Party is " + value[0].get('BuyerPartyID') + "."
            } )
            
    elif intent == "get-pos":
        value = data.get('d').get('results')
        items = []
        i = 0
        if len(value) <= 5:
            j = len(value)
        else:
            j = 5
        while i < j:
            items.append(
                {
                    "optionInfo": {
                    "key": "PO",
                    "synonyms": ["PO"]
                    },
                    "title": "PO ID: " + value[i].get('PurchaseOrderID'),
                    "description": value[i].get('PurchaseOrderLifeCycleStatusCodeText')
                })
            i += 1
        
        speech = "Here are the requested details"
        messages.append( {                                             
                "items": items,
                "title": "List of POs",
                "platform": "google",
                "type": "list_card"
            } )
        
        messages.append( {
              "type": 0,
              "speech": "Supplier of PO " + value[0].get('PurchaseOrderID') + " is " +  value[0].get('SellerPartyID') + ". " + \
                         "Total Net Value is " + value[0].get('TotalNetAmount') + " " + value[0].get('CurrencyCodeText') + ". " + \
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
        messages.append( {
              "type": 0,
              "speech": speech
            } )
    elif intent == "po-action":
        value = data.get('d').get('results')
        node_id = value.get('ObjectID')
        speech = "The status of Purchase Order ID " + str(value.get('PurchaseOrderID')) + \
             	 " is " + value.get('PurchaseOrderLifeCycleStatusCodeText')
        messages.append( {
              "type": 0,
              "speech": speech
            } )
    elif intent == "record-time":
        speech = "Time sheet was updated successfully!"
        messages.append({
            "type": 0,
            "speech": speech
        })        
    else:
        speech = "Sorry, I did not understand you! Please try again"
        messages.append( {
              "type": 0,
              "speech": speech
            } )
    
    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        "messages": messages,
        #"contextOut": node_id,
        "source": "bydassistant"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

app.run(debug=False, port=port, host='0.0.0.0')
