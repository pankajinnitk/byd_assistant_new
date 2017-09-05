
import requests
import xmltodict

from requests.auth import HTTPBasicAuth
report_name = ''
dict_props = {}
dict_type = {}

def parseXML(report_query_name):
    base_url = 'https://my316075.sapbydesign.com/sap/byd/odata/cc_home_analytics.svc/$metadata?entityset={}&sap-language=EN'.format(report_query_name)

    try:
        res = requests.get(base_url, auth=HTTPBasicAuth('administration01', 'Welcome1'))
        xml_data = xmltodict.parse(res.text)
        data_properties = xml_data['edmx:Edmx']['edmx:DataServices']['Schema']['EntityType']['Property']
        report_name = xml_data['edmx:Edmx']['edmx:DataServices']['Schema']['EntityType']['@sap:label']
        for value in data_properties:
            if '@Name' in value and '@sap:label' in value:
                prop_key = value['@Name']
                prop_value = value['@sap:label']
                temp_dict = {prop_key : prop_value}
                dict_props.update(temp_dict)

                prop_value = value['@Type']
                temp_dict = {prop_key : prop_value}
                dict_type.update(temp_dict) 

    except RuntimeError as odata_failed_exception:
        print('odata query failed! {}'.format(odata_failed_exception))


def get_prop_name(prop_key):
    if dict_props is not None:
        if prop_key in dict_props:
            return dict_props[prop_key]

def get_report_name():
    if report_name is not '':
        return report_name
          
def is_decimal(prop_key):
    if prop_key in dict_type:
        if dict_type[prop_key] == 'Edm.Decimal':
            return True
        else:
            return False 
