import base64
import analytics
import json
import os
import requests 
import odataparse

from flask import request
from flask import make_response

def run(req):
    res = processRequest(req)
    res = json.dumps(res, indent=4)
    print("Response:")
    print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r

def processRequest(req):
    session = requests.Session()

    baseurl = "https://my316075.sapbydesign.com/sap/byd/odata/cc_home_analytics.svc/"
    session.headers.update({'authorization' : "Basic " + base64.encodestring(('%s:%s' % ("administration01", "Welcome1")).encode()).decode().replace('\n', '')})
    session.headers.update({'x-csrf-token' : 'fetch'})
    print(session)
    res = session.get(baseurl, data = {'user' :'administration01','password' : 'Welcome1'}, proxies = "")
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
	
    intent = result.get("action")
    if intent == "analytics":
        parameters = result.get("parameters")
        filter_ids = parameters.get("analytics-entities")
        values = parameters.get("entity-value")
        reportid = parameters.get("report-id")
        odataparse.parseXML(reportid)
        select_a = parameters.get("select-param-entities")
        select = ",".join(select_a)
        filters = ""
        j = len(filter_ids)
        i = 0
        while i < j:
            if i > 0:
                string = ' and ' + filter_ids[i] + ' eq ' + "'" + values[i] + "'"
            else:                
                string = filter_ids[i] + ' eq ' + "'" + values[i] + "'"
            filters += ''.join(string)
            i += 1

        return "get" , reportid + "?" "$select=" + select + "&$filter=" + filters + "&$format=json"
    else:
        return {}
	
def makeWebhookResult(data, req):
    messages = []
    intent = req.get("result").get("action")
    parameters = req.get("result").get("parameters")
    select = parameters.get("select-param-entities")
    if intent == "analytics":		        
        value = data.get('d').get('results')
        select = parameters.get("select-param-entities")
        items = []
        i = 0
        if len(select) <= 5:
            j = len(select)
        else:
            j = 5
        while i < j:
            if odataparse.is_decimal(select[i]):
                desc = "%.2f" % float(value[0].get(select[i])) + " USD"
            else:
                desc = value[0].get(select[i])
            items.append(
                {
                    "optionInfo": {
                    "key": "EVA",
                    "synonyms": ["EVA"]
                    },
                    "title": odataparse.get_prop_name(select[i]),
                    "description": desc
                })
            i += 1
        
        speech = "Here are the requested details"
        messages.append( {                                             
                "items": items,
                "title": odataparse.get_report_name(),
                "platform": "google",
                "type": "list_card"
            } )
        
        i = 0
        j = len(select)
        while i < j:
            text = odataparse.get_prop_name(select[i]) + ' - ' + value[0].get(select[i]) + "."
            default = ''.join(text)
            i += 1

        messages.append( {
              "type": 0,
              "speech": default
            } )

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
