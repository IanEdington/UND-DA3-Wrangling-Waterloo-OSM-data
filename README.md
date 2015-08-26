
# Wrangling Waterloo OSM data
## Waterloo, ON, Canada By @IanEdington

Full report at: https://github.com/IanEdington/wrangling-waterloo-maps-data

#### Map Area: Region of Waterloo, ON, Canada
   * [https://www.openstreetmap.org/relation/2062154](https://www.openstreetmap.org/relation/2062154)
   * [https://www.openstreetmap.org/relation/2062153](https://www.openstreetmap.org/relation/2062153)

#### References used during this project
   * [http://docs.mongodb.org/manual/reference/](http://docs.mongodb.org/manual/reference/)
   * [https://docs.python.org/2/library/re.html](https://docs.python.org/2/library/re.html)
   * [https://docs.python.org/3/library/xml.etree.elementtree.html](https://docs.python.org/3/library/xml.etree.elementtree.html)
   * [http://stackoverflow.com/questions/5029934/](http://stackoverflow.com/questions/5029934/)
   * [http://stackoverflow.com/questions/16614648/](http://stackoverflow.com/questions/16614648/)

## 1. Problems Encountered in the Map
Over four iteration a lot of challenges were identified in the data cleaning & transforming process. An overview of the problems identified are in the document bellow for the step by step process that I went throught to understand, structure and clean the data please see the [Wrangling Waterloo OSM journal](https://github.com/IanEdington/wrangling-waterloo-maps-data/blob/master/Wrangling%20Waterloo%20OSM.ipynb).

###Problem areas identified:

#### element attributes

* The following attributes should be integers instead of strings:

        uid
        version      
        changeset    
        id           
        nd ref       
        relation ref 

#### nd tags:
* 'nd' tags are always ints and the order they appears is important. The best way to store this data in JSON is as an array of ints.

#### member tags:
* Member tags contain complex information and their order matters. The best way to store this data in JSON is as an array of objects. 

        'member': [{'type': sub_tag.attribute.get('type'),
                    'ref':  sub_tag.attribute.get('ref'),
                    'role': sub_tag.attribute.get('role')},
                    {...},
                    {...}]

* Sometimes the 'role' attribute of member tags is undefined. This can be removed to simplify the JSON document.

        role of "" -> None

#### tag values:
* Tag values can overlap with attributes so should be kept in their own objects

* 'FIXME' and 'fixme' tags both exist. They should be standardized

* 'note' and 'note_1' tags both exist. They should be standardized

#### tag values (address):
##### addr:street
* tdcanadatrust.com shouldn't be an address. It should be changed to a URL.

* These are street directions that should be standardized:
            South, S, s -> South
            East,  E, e -> East
            West,  W, w -> West
            North, N, n -> North

* These are street types that should be standardized even if infront of a street direction:

            AVenue Ave    -> Avenue
            Cresent       -> Crescent
            Dr Dr.        -> Drive
            Rd            -> Road
            St St. Steet  -> Street

##### addr:state should be empty
        if province is populated:
            disregard state
        else:
            assign state to province

##### addr:province should be all 'ON'
    
##### addr:interpolation Yes is not a valid value
* If Yes exists as a value for addr:interpolation a 'FIXME' tag should be added saying 'Yes is not a valid entry for addr:interpolation'
    
##### addr:city
* These are city names that should be standardized:
        'City of Cambridge' -> 'Cambridge'
        'City of Kitchener' -> 'Kitchener'
        'kitchener'         -> 'Kitchener'
        'City of Waterloo'  -> 'Waterloo'
        'waterloo'          -> 'Waterloo'
        'St. Agatha'        -> 'Saint Agatha'

#### Programatically edited:
Most of these problems were handled programatically with the process_map function of Lasso.py. A few acceptions are listed in the following section.

#### Manually edited:
A programatic fix wasn't appropriate for a few problems, most likely due to human error. The following errors were changed in the OSM XML document.

* the addr:interpolation of Yes
* the addr:street of tdcanadatrust.com was changed to a url
* a 'note' starting with 'FIXME:' was changed to a 'FIXME'
* a few elements with 'note' and 'note_1' were combined into 'note'
    

### Final Data Structure
The final data structure was designed to hold all the data in an easily accessible and organized way.

    {'type':    xml_tree.tag,

     'id':      int(xml_tree('id')),

     'pos':     [float(xml_tree('lat')),
                 float(xml_tree('lon'))],

     'created': {'version':     int(xml_tree('uid')),
                 'changeset':   int(xml_tree('changeset')),
                 'timestamp':   xml_tree('timestamp'),
                 'user':        xml_tree('user'),
                 'uid':         int(xml_tree('uid'))},

     'address': {'housenumber': tag_tag['addr:housenumber'],
                 'postcode': tag_tag['addr:postcode'],
                 'street': tag_tag['addr:street'],
                 ...},

     'member':  [{'type': member_tag('type'),
                  'ref':  int(member_tag('ref')),
                  'role': member_tag('role')},
                 {..........................}],

     'node_refs':[int(nd_tag['ref']),
                  int(nd_tag['ref']), ... ],

     'tag': {tag['k']:  tag_tag['v'],
             tag['k']:  tag_tag['v'],
             ... }
     }

#### Process full dataset with manual fixes:


    from collections import defaultdict
    
    #-- Import wrangling functions using my lasso
    import Lasso as l


    osmfile = 'waterloo-OSM-data.osm'
    json_sample = l.process_map(osmfile)

#### Import into Mongo DB using mongoimport

    from xml_tree:
    node:     248,288
    way:       31,662
    relation:     234
    total:    280,184

    $ mongoimport -d osm -c elements --file waterloo-OSM-data.osm.json
    >>> imported 280184 documents

##2. Data Overview
Student provides a statistical overview about their chosen dataset, like:


    from pymongo import MongoClient
    client = MongoClient('localhost:27017')
    osm = client.osm

####size of the file: 

    original OSM xml: 55,692,326 bytes
    JSON:             59,418,687 bytes
    MongoDB:         201,326,592 bytes


    osm.command("dbstats")




    {'avgObjSize': 276.87786771738973,
     'collections': 3,
     'dataFileVersion': {'major': 4, 'minor': 22},
     'dataSize': 77577856.0,
     'db': 'osm',
     'extentFreeList': {'num': 0, 'totalSize': 0},
     'fileSize': 201326592.0,
     'indexSize': 9108064.0,
     'indexes': 1,
     'nsSizeMB': 16,
     'numExtents': 12,
     'objects': 280188,
     'ok': 1.0,
     'storageSize': 86323200.0}



####number of unique users & top 5 contributors:


    pipeline = [{'$group': {'_id': '$created.uid',
                            'user': {'$first': '$created.user'},
                            'count': {'$sum':1}}},
                {'$sort': {'count': -1}}]
    
    users = osm.elements.aggregate(pipeline)['result']
    
    print('There were ' + str(len(users)) + ' unique users who contributed to the Waterloo Map.\n')
    
    for ur in users[:5]:
        print (ur['user'] + ' added ' + str(ur['count']) + ' elements')

    There were 321 unique users who contributed to the Waterloo Map.
    
    permute added 127990 elements
    fuego added 30268 elements
    andrewpmk added 28966 elements
    rw__ added 20155 elements
    Xylem added 12611 elements


####number of nodes, ways, and relations:


    pipeline = [{'$group': {'_id': '$type',
                            'count': {'$sum':1}}},
                {'$sort': {'count': -1}}]
    
    elementTypes = {}
    
    for ty in osm.elements.aggregate(pipeline)['result']:
        elementTypes[ty['_id']] = ty['count']
        print ('There are ' + str(ty['count']) +' '+ ty['_id'] +' elements')

    There are 248288 node elements
    There are 31662 way elements
    There are 234 relation elements


###3. Additional Ideas

The Region of Waterloo has a large amount of open data part of which is map data related to bike routs. Although some of the routs are in OSM not all are. The data from Waterloo is updated annually and there should be a way to automate an annual import, matching already imported data.

With the increase of cyclists there might be an opportunity for a bike friendly GPS app. Since a lot of cyclists feel a sense of comradery with other cyclists, building a comunity around what roads are good for different bikers might be a good way to insight high quality data. As we can see below there is very little in terms of bicycle data on OSM for Waterloo.

#### Bikeable ways verses non bikeable ways


    pipeline = [{'$match': {'tag.bicycle': {'$exists':1},
                            'type': 'way'}},
                {'$group': {'_id': '$tag.bicycle',
                            'count': {'$sum':1}}},
                {'$sort': {'count': -1}}]
    
    bikeWays = {}
    
    for bkW in osm.elements.aggregate(pipeline)['result']:
        bikeWays[bkW['_id']] = bkW['count']
        print ('There are '+ str(bkW['count']) +' '+ bkW['_id'] +' ways in KW.')
    
    print ('Out of ' + str(elementTypes['way']) + ' ways ' + str(bikeWays['yes'] + bikeWays['designated']) +' are bike friendly, marked as yes or designated.')

    There are 1617 yes ways in KW.
    There are 295 designated ways in KW.
    There are 138 no ways in KW.
    There are 3 permissive ways in KW.
    There are 2 dismount ways in KW.
    Out of 31662 ways 1912 are bike friendly, marked as yes or designated.


####Amenities containing the word bicycle


    pipeline = [{'$match': {'type': 'node',
                            'tag.amenity': {'$regex': r'bicycle',
                                            '$options': 'i'}}},
                {'$group': {'_id': '$tag.amenity',
                            'count': {'$sum':1}}},
                {'$sort': {'count': -1}}]
    
    bikeSpots = {}
    
    for bk in osm.elements.aggregate(pipeline)['result']:
        bikeSpots[bk['_id']] = bk['count']
        print (bk['_id']+'  count: ' + str(bk['count']))

    bicycle_parking  count: 83
    bicycle_repair_station  count: 6

