'''

'''

import xml.etree.cElementTree as ET
import re
import codecs
import json
from collections import defaultdict


#  Regex
RE_PROBLEM_CHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
RE_POSTAL_CODE = re.compile(r"^([a-zA-Z]\d[a-zA-Z]( )?\d[a-zA-Z]\d)$")
    #http://stackoverflow.com/questions/16614648/canadian-postal-code-regex

# Default Dicts used in audit functions
def S_D(): return defaultdict(lambda : defaultdict(set))
def S_DD(): return defaultdict(lambda : defaultdict(lambda : defaultdict(set)))


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

def process_audit_address_type(tag_k_v_dict, directions=()):
    street_types = set()
    street_list = wrap_up_tag_k_v_dict(tag_k_v_dict, 'addr:street')

    for v in list(street_list):
        street_name = v
        street_split = street_name.split()
        if street_split[-1] in directions:
            street_types.add(street_split[-2])
        else:
            street_types.add(street_split[-1])

    return street_types

def wrap_up_tag_k_v_dict(tag_k_v_dict, key):
    return tag_k_v_dict['node'][key] | tag_k_v_dict['node'][key] | tag_k_v_dict['way'][key]


##############################
### Load Data into MongoDB ###
##############################

def shape_xml_tree(xml_tree):
    '''
    takes xml tree with tag 'node', 'way', or 'relation'

    Unpackes into json compatible dict and list structure.
    returns dictionary
    {
     'type':    xml_tree.tag
     'id':      xml_tree.attrib.get('id')
     'pos':     [float(xml_tree.attrib.get('lat')),
                 float(xml_tree.attrib.get('lon'))]
     'created': {'version':     '2',
                 'changeset':   '17206049',
                 'timestamp':   '2013-08-03T16:43:42Z',
                 'user':        'linuxUser16',
                 'uid':         '1219059'},
     'address': {'housenumber': '5157',
                 'postcode': '60625',
                 'street': 'North Lincoln Ave'},
     'member':  [{'type': sub_tag.attribute.get('type'),
                  'ref':  sub_tag.attribute.get('ref'),
                  'role': sub_tag.attribute.get('role')},
                 {.....................................}],
     'node_refs':[sub_tag.attrib['ref'],
                  sub_tag.attrib['ref']],

     tag['k']:  sub_tag.attrib['v'],
     }

    '''
    if xml_tree.tag not in ['node', 'way', 'relation']:
        return {}

    element = {}

    ### Tag:
    element['type'] = xml_tree.tag

    ### Attributes:
    element['id'] = int(xml_tree.attrib.get('id'))

    if xml_tree.tag == 'node':
        pos = [float(xml_tree.attrib.get('lat')), float(xml_tree.attrib.get('lon'))]
        element['pos'] = pos

    element['created'] = {}
    for key, val in xml_tree.attrib.items():
        if key in ["uid", "version", "changeset"]:
            element['created'][key] = int(val)
        if key in ["user", "timestamp"]:
            element['created'][key] = val

    ### sub tags of xml_tree
    node_refs = []
    members = []
    address = {}
    for sub_tag in xml_tree.iter():
        ### sub tag of 'tag'
        if sub_tag.tag == 'tag':
            if not RE_PROBLEM_CHARS.search(sub_tag.attrib['k']):
                if sub_tag.attrib['k'][0:5]== 'addr:':
                    address[sub_tag.attrib['k'][5:]] = sub_tag.attrib['v']
                else:
                    element[sub_tag.attrib['k']] = sub_tag.attrib['v']
        ### sub tag of 'nd'
        elif sub_tag.tag == 'nd':
            node_refs.append(int(sub_tag.attrib['ref']))
        ### sub tag of 'member'
        elif sub_tag.tag == 'member':
            mem = {}
            for k, v in sub_tag.attrib.items():
                if v:
                    if k == 'ref':
                        mem[k] = int(v)
                    else:
                        mem[k] = v
            members.append(mem)
    if node_refs:
        element['nd'] = node_refs
    if members:
        element['member'] = members
    if address:
        element['addr'] = address

    return element

def process_map(file_in, pretty = False):
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, xml_tree in ET.iterparse(file_in):
            element = shape_xml_tree(xml_tree)
            if element:
                data.append(element)
                if pretty:
                    fo.write(json.dumps(element, indent=4)+"\n")
                else:
                    fo.write(json.dumps(element) + "\n")
    return data

if __name__ == '__main__':
    pass
