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
RE_LOWER = re.compile(r'^([a-z]|_)*$')
RE_LOWER_COLON = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
RE_PROBLEM_CHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

# Default Dicts used in audit functions
S_D = defaultdict(set)
S_DD = defaultdict(lambda : defaultdict(int))

#
EXPECTED_STREET_NAMES = []
STREET_NAME_MAPPING = { "St": "Street",
                    "St.": "Street",
                    }
CREATED = [ "version", "changeset", "timestamp", "user", "uid"]


def audit_tags_2_deep(element, atr_d=S_D, st_atr_d=S_DD, s_st_d=S_D, tag_k_v_dict=S_D):
    '''
    take a start xml tag

    return:
        1 - attrib_dict (atr_d): should return all potential attributes with a set of all answers
        2 - sub_tag_attrib_dict (st_atr_d): return sub_tag: sub_tag.attrib.keys()
        3 - sub_subtag_dict (s_st_d): return sub_tag: sub_tag.children
        4 - tag_k_v_dict: for tag sub_tag:
    '''
    for key, val in element.attrib.items():
        atr_d[key].add(val)
    for _, sub_tag in element.iter():
        for key, val in sub_tag.attrib.items():
            st_atr_d[sub_tag.tag][key].add(val)
        s_st_d[sub_tag.tag].add(sub_tag.getchildren()) # hopefully none (nested only one deep)
        if sub_tag.tag == 'tag':
            tag_k_v_dict[sub_tag.attrib['k']].add(sub_tag.attrib['v'])

    return atr_d, st_atr_d, s_st_d, tag_k_v_dict

def audit_count_tags(filename):
    # read osm into xml without loading the entire file
    xml_tree = ET.iterparse(filename)

    tag_dict = defaultdict(int)
    for (_, elem) in xml_tree:
        tag_dict[elem.tag] += 1
    return tag_dict

def audit_key_type(element, keys):
    if element.tag == "tag":
        if RE_LOWER.search(element.attrib['k']):
            keys['lower'] +=1
        elif RE_LOWER_COLON.search(element.attrib['k']):
            keys['lower_colon'] +=1
        elif RE_PROBLEM_CHARS.search(element.attrib['k']):
            keys['problemchars'] +=1
        else:
            keys['other'] +=1
    return keys

def audit_street_type(street_types, street_name):
    '''
    get:
        street_types = defaultdict(set)
        street_name = string of street name
    return:
        street_types dict with {'last word of street_name': street_name}
    '''
    m = RE_LAST_WORD.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in EXPECTED_STREET_NAMES:
            street_types[street_type].add(street_name)

def process_audit_street_type(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for _, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if (tag.attrib['k'] == "addr:street"):
                    audit_street_type(street_types, tag.attrib['v'])

    return street_types


def update_name(name, mapping):
    m = RE_LAST_WORD.search(name)
    street_type = m.group()
    better_name = RE_LAST_WORD.sub(mapping[street_type], name)
    return better_name

def process_update_name():
    st_types = process_audit_street_type('example.osm')
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
    node = S_D.copy()
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
