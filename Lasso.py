'''

'''

import xml.etree.cElementTree as ET
import re
import codecs
import json
from collections import defaultdict
from pprint import pprint


# Commonly used Regex
RE_LAST_WORD = re.compile(r'\b\S+\.?$', re.IGNORECASE)
RE_SECOND_LAST_WORD = re.compile(r'\b\S+\.?$', re.IGNORECASE)
RE_LOWER = re.compile(r'^([a-z]|_)*$')
RE_LOWER_COLON = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
RE_PROBLEM_CHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

# Default Dicts used in audit functions
def S_D(): return defaultdict(lambda : defaultdict(set))
def S_DD(): return defaultdict(lambda : defaultdict(lambda : defaultdict(set)))

#
EXPECTED_STREET_NAMES = []
STREET_NAME_MAPPING = { "St": "Street",
                    "St.": "Street",
                    }
CREATED = [ "version", "changeset", "timestamp", "user", "uid"]


#########################
### Auditing the data ###
#########################

def dictify_element_and_children(element, atr_d=S_D(), st_atr_d=S_DD(), s_st_d=S_D(), tag_k_v_dict=S_D()):
    '''
    take a start xml tag

    return:
        1 - attrib_dict (atr_d): should return all potential attributes with a set of all answers
        2 - sub_tag_attrib_dict (st_atr_d): return sub_tag: sub_tag.attrib.keys()
        3 - sub_subtag_dict (s_st_d): return sub_tag: sub_tag.children
        4 - tag_k_v_dict: for tag sub_tag:
    '''
    for key, val in element.attrib.items():
        atr_d[element.tag][key].add(val)
    for sub_tag in element.iter():
        child_set = {el.tag for el in list(sub_tag)}
        if child_set != set():
            s_st_d[element.tag][sub_tag.tag].update(child_set)
        for key, val in sub_tag.attrib.items():
            st_atr_d[element.tag][sub_tag.tag][key].add(val)
        if sub_tag.tag == 'tag':
            tag_k_v_dict[element.tag][sub_tag.attrib['k']].add(sub_tag.attrib['v'])

    return atr_d, st_atr_d, s_st_d, tag_k_v_dict

def summarizes_data_2_tags_deep(filename):
    atr_d=S_D()
    st_atr_d=S_DD()
    s_st_d=S_D()
    tag_k_v_dict=S_D()

    for _, element in ET.iterparse(filename):
        dictify_element_and_children(element, atr_d, st_atr_d, s_st_d, tag_k_v_dict)
    return atr_d, st_atr_d, s_st_d, tag_k_v_dict

def check_keys_list(dict_key_list):
    problem_keys = []
    for key in dict_key_list:
        if RE_PROBLEM_CHARS.search(key):
            problem_keys.append(key)
    return problem_keys

def audit_street_type(street_types, street_name, regex = RE_LAST_WORD):
    '''
    get:
        street_types = defaultdict(set)
        street_name = string of street name
    return:
        street_types dict with {'last word of street_name': street_name}
    '''
    m = regex.search(street_name)
    street_directions = ['N', 'North', 'E', 'East', 'South', 'West', 'W',]
    if m:
        street_type = m.group()
        if street_type in street_directions:
            street_types[street_name.split()[-2]].add(street_name)
        else:
            street_types[street_type].add(street_name)

def process_audit_address_type(osmfile, addr_v = "addr:street", regex = RE_LAST_WORD):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for _, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "tag":
            if (elem.attrib['k'] == addr_v):
                audit_street_type(street_types, elem.attrib['v'], regex)
    return street_types

#########################
###  ###
#########################

def update_name(name, mapping):
    m = RE_LAST_WORD.search(name)
    street_type = m.group()
    better_name = RE_LAST_WORD.sub(mapping[street_type], name)
    return better_name

def process_update_name():
    st_types = process_audit_address_type('example.osm')
    pprint(dict(st_types))

    for _, ways in st_types.items():
        for name in ways:
            better_name = update_name(name, STREET_NAME_MAPPING)
            print (name, "=>", better_name)
            if name == "West Lexington St.":
                assert better_name == "West Lexington Street"
            if name == "Baldwin Rd.":
                assert better_name == "Baldwin Road"

def shape_element(element):
    node = S_D()
    if element.tag == "node":
        node['type'] = 'node'
        pos = [float(element.attrib.get('lat')), float(element.attrib.get('lon'))]
        node['pos'] = pos
    elif element.tag == "way":
        node['type'] = 'way'
    else:
        return {}

    for key, val in element.attrib.items():
        if key not in ["lat", "lon"]:
            if key in ["changeset", "user", "version", "uid", "timestamp"]:
                node['created'][key] = val
            else:
                node[key] = val

    node_refs = []
    for sub_elem in element.iter():
        if sub_elem.tag == 'tag':
            if not RE_PROBLEM_CHARS.search(sub_elem.attrib['k']):
                if sub_elem.attrib['k'][0:5]== 'addr:':
                    if ':' not in sub_elem.attrib['k'][5:]:
                        node['address'][sub_elem.attrib['k'][5:]] = sub_elem.attrib['v']
                else:
                    node[sub_elem.attrib['k']] = sub_elem.attrib['v']
        elif sub_elem.tag == 'nd':
            node_refs.append(sub_elem.attrib['ref'])
    if node_refs:
        node['node_refs'] = node_refs

    node = dict(node)
    return node

def process_map_2(file_in, pretty = False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=4)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data


def process_map_3(filename):
    '''https://docs.python.org/3.4/library/stdtypes.html#set.add'''
    users = set()
    for _, element in ET.iterparse(filename):
        users.add(element.attrib.get('user'))
    users.remove(None)
    return users


if __name__ == '__main__':
    pass
