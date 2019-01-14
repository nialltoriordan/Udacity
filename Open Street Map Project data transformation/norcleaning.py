'''
This script parses a XML file, cleans the data and stores it in a python dictionary.  The data is then outputted as JSON.

The 'cleaning' has four elements :

1 : Nodes are processed to ensure they are valid.
2 : Building and address data is standardised (see processWay() function).
3 : Data is reshapped - address data reshaped as a dictionary, relation data reshaped, etc.
4 : Key values are checked for invalid characters (that cannot be inserted in mongodb).

Note : this program is based on the code provided in the OSM case study.
'''

import json
import pprint
import re
import xml.etree.cElementTree as ET
import codecs

SOURCE_FILE = 'dublin_tenth.osm'
INTERMEDIATE_FILE = 'dublin_tenth.json'

ROOF_SHAPES = [ "flat", "pitched", "sloped", "dome"]


problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

invalid_node_count = 0
problemchar_count = 0


'''
This function simply checks if the "k" value of a tag begins with "addr:" or "address"
'''
def isAddr(tag):
    #check if tag.attrib['k'] contains 'addr:' or 'address'
	keyString = tag.attrib['k']
	if (keyString.startswith("addr:")) or (keyString == "address") :
		return True
 
	return False
	
'''
The osm files don't have standard keys for address data.  This function simply checks type of address tags and returns a dictionary with the key and value. 

If the tag 'k' begins with "addr:", the key is split and a modified key and value returned.
Example : <tag k="addr:street" v="North Circular Road" /> becomes { "street" : "North Circular Road" }

Note : no further splitting is done if a tag has more than one ":", so "addr:housename:ga" for example would become "housename:ga".



If the tag 'k' is "address", it's checked to see if it begins with a number.  If yes, it assumed it's an address and split.
Example : <tag k="address" v="43/45 Northumberland Road"/> becomes { "housenumber" : "43/45" ,  "street" : "Northumberland Road" }

Otherwise it's assumed it's a housename.
Example : <tag k="address" v="Island Key"/> becomes { "housename" : "Island Key" }
'''
def getAddrValue(tag):

	keyString = tag.attrib['k']
	if keyString == "address" :
		if tag.attrib['v'][0].isdigit() :
			myList = tag.attrib['v'].split(" ")
			myDict = { "housenumber" : check_problemchars(myList[0])}
			myList.pop(0)
			myDict["street"] = check_problemchars(" ".join(myList)) 
		else :
			myDict = { "housename" : check_problemchars(tag.attrib['v'])}
	else :
		myDict = { tag.attrib['k'][5:] : check_problemchars(tag.attrib['v'])}
		
	return myDict
	


'''
This function simply checks if the "k" value of a tag begins with "building"
'''
def isBuilding(tag):
    #check if tag.attrib['k'] contains 'building'
    keyString = tag.attrib['k']
    if keyString.startswith("building") :
        return True
        
    return False
	
'''
The osm files don't have standard keys for building data.  This function simply checks type of building tags and returns a dictionary with the split tag and value. 
Example : <tag k="building:levels" v="5" /> becomes { "levels" : "5" }
Example : <tag k="building" v="apartments" /> becomes { "type" : "apartments" }

Tags that contain the following 'k' :

  "building-roof-shape" 
  "building:roof" 
  "building:roof:shape" 
  "building:roof:type" 
  "building:roof_shape"
  
 are reshaped.  If the correspoding 'v' value is a roof shape, it's added to a "roof:shape" dictionary element.
Example : <tag k="building-roof-shape" v="pitched"/> becomes { "roof:shape" : "pitched" }
 
Otherwise it is assumed it is a roof type and added to a "roof:type" dictionary element.
Example : <tag k="building:roof" v="tile"/> becomes { "roof:type" : "tile" }

Also if a value is "sloped" it is standardised to "pitched", and "tiled" is standardised to "tile".
'''
def getBuildingValue(tag):
	keyString = tag.attrib['k']
	if keyString == "building" :
		myDict = { "type" : check_problemchars(tag.attrib['v'])}
	else :
		if "roof" in tag.attrib['k'] :		
			if tag.attrib['v'] in ROOF_SHAPES :
				if tag.attrib['v'] == "sloped" :
					myDict = { "roof:shape" : "pitched" }
				else :
					myDict = { "roof:shape" : check_problemchars(tag.attrib['v']) }
			else :
				if tag.attrib['v'] == "tiled" :
					myDict = { "roof:type" : "tile" }
				else :
					myDict = { "roof:type" : check_problemchars(tag.attrib['v']) }
		else :
			myDict = { tag.attrib['k'][9:] : check_problemchars(tag.attrib['v'])}
		
	return myDict

	
'''
This function takes strings with problem characters and attempts to resolve them.

If a string begins with "#" or "+", it is removed from the start of the string.
If a string begins with "+ ", the first two characters are removed from the start of the string.
If a string is just a "." or "?", "empty" is returned.
Otherwise the string is returned unchanged.
'''	
def tryFixValue(myString):
	
	if myString.startswith("+ ") :
		return myString[2:]
	elif myString.startswith("#") or myString.startswith("+") :
		return myString[1:] 
	elif myString == "." or myString == "?" :
		return "empty"
	else :
		return myString
		
'''
This function checks for problem characters that cannot be used within keys in mongodb.  If problem characters are found, 
the tryFixValue() function is called.  The string is rechecked for problem characters and if any are found, "invalid" is
returned.

Note that I'm also assuming that keys themselves are okay : that keys conform to standard and have no problem characters.
'''
def check_problemchars(myString):
	global problemchar_count

	if not problemchars.match(myString) :
		return myString
	else:
		myString = tryFixValue(myString)
		if not problemchars.match(myString) :
			return myString
		else :
		
			problemchar_count += 1
			return "invalid"

		
'''
This function processes nodes.  The node if checked if it is valid.  At the moment no action is taken for invalid nodes; a 
count is incremented and an empty dictionary node returned.  A valid node must have 'id', 'lat' and 'lon'.
 
If a node contains address data, it is reshaped - if the second level tag "k" value starts with "addr:", it is added to a dictionary "address".
Update : Some nodes contain one or more 'building' tags.  I'm going to reshape building data here too for consistency.
'''
def processNode(element):
	node = {}
	global invalid_node_count
	
	if ('id' in element.attrib) and ('lat' in element.attrib) and ('lat' in element.attrib ): #check if valid node
		node["id"] = check_problemchars(element.attrib['id'])
		node["lat"] = check_problemchars(element.attrib['lat'])
		node["lon"] = check_problemchars(element.attrib['lon'])

		if 'changeset' in element.attrib :
			node["changeset"] = check_problemchars(element.attrib['changeset'])
		if 'timestamp' in element.attrib :
			node["timestamp"] = check_problemchars(element.attrib['timestamp'])
		if 'uid' in element.attrib :
		    node["uid"] = check_problemchars(element.attrib['uid'])
		if 'user' in element.attrib :
		    node["user"] = check_problemchars(element.attrib['user'])
		if 'version' in element.attrib :
			node["version"] = check_problemchars(element.attrib['version'])
		for tag in element.iter("tag") :
			if isAddr(tag) :  
				if "address" in node.keys():
					#if dictionary already has an 'address' dictionary, update it
					node["address"].update(getAddrValue(tag))  #note - check for problem chars is done in this function for readability
				else :
					#else, create address dictionary
					node["address"] = getAddrValue(tag)
			elif isBuilding(tag) :  
				'''
				Building type sometimes set to "yes".  Might be able to improve this.
				'''
				if "building" in node.keys():
					#if dictionary already has an 'building' dictionary, update it
					node["building"].update(getBuildingValue(tag))  #note - check for problem chars is done in this function for readability
				else :
					#else, create building dictionary
					node["building"] = getBuildingValue(tag)	
			else :
				node[tag.attrib['k']] = check_problemchars(tag.attrib['v'])
	else:
		invalid_node_count += 1
		
	return node
	
'''
This function processes way elements.  A lot of the code is similar to the previous function and might be better put in a sub-function.  I'm
going to keep it this way for now, to make it easier to update how one type of element is processed without affecting others.

If a way element contains address data, it is reshaped - if the second level tag "k" value starts with "addr:", it is added to a dictionary "address".
"building" tags are also reshaped - if the second level tag "k" value starts with "building", it is added to a dictionary "building".
If a way element contains one or more "nd" tags, they are added to a "nd" list.

For more on standardisation of address and building data, see the getAddrValue() and getBuildingValue() functions.
'''
def processWay(element):
	node = {}
	
	if 'changeset' in element.attrib :
		node["changeset"] = check_problemchars(element.attrib['changeset'])
	if 'id' in element.attrib :
	    node["id"] = check_problemchars(element.attrib['id'])
	if 'timestamp' in element.attrib :
	    node["timestamp"] = check_problemchars(element.attrib['timestamp'])
	if 'uid' in element.attrib :
	    node["uid"] = check_problemchars(element.attrib['uid'])
	if 'user' in element.attrib :
	    node["user"] = check_problemchars(element.attrib['user'])
	if 'version' in element.attrib :
	    node["version"] = check_problemchars(element.attrib['version'])
	for tag in element.iter() :
		if (tag.tag == "nd") :
			if "nd" in node.keys() :
				#if list already exists, append to list   
				node["nd"].append(check_problemchars(tag.attrib['ref']))
			else :
				#else create "nd" list 
				node["nd"] = [check_problemchars(tag.attrib['ref'])]
		elif (tag.tag == "tag") :
			if isAddr(tag) :  
				if "address" in node.keys():
					#if dictionary already has an 'address' dictionary, update it
					node["address"].update(getAddrValue(tag))  #note - check for problem chars is done in this function for readability
				else :
					#else, create address dictionary
					node["address"] = getAddrValue(tag)
			elif isBuilding(tag) :  
				'''
				Building type sometimes set to "yes".  Might be able to improve this.
				'''
				if "building" in node.keys():
					#if dictionary already has an 'building' dictionary, update it
					node["building"].update(getBuildingValue(tag))  #note - check for problem chars is done in this function for readability
				else :
					#else, create building dictionary
					node["building"] = getBuildingValue(tag)		
			else :
				node[tag.attrib['k']] = check_problemchars(tag.attrib['v'])  #this should be unnecessary, as all tags dealth with
	
	return node

	
'''
This function processes relation elements.  Again, a lot of the code is similar to the previous functions and might be better put in a sub-function.  I'm
going to keep it this way for now, to make it easier to update how one type of element is processed without affecting others.

If a relation element contains address data, it is reshaped - if the second level tag "k" value starts with "addr:", it is added to a dictionary "address".
Attributes from memmber elements are stored in a dictionary, which are stored in a list of dictionarys.
'''	
def processRelation(element):
	node = {}
	
	if 'changeset' in element.attrib :
            node["changeset"] = check_problemchars(element.attrib['changeset'])
	if 'id' in element.attrib :
	    node["id"] = check_problemchars(element.attrib['id'])
	if 'timestamp' in element.attrib :
	    node["timestamp"] = check_problemchars(element.attrib['timestamp'])
	if 'uid' in element.attrib :
	    node["uid"] = check_problemchars(element.attrib['uid'])
	if 'user' in element.attrib :
	    node["user"] = check_problemchars(element.attrib['user'])
	if 'version' in element.attrib :
	    node["version"] =check_problemchars(element.attrib['version'])
	for tag in element.iter() :	
		'''	
		Leaving these comments here for final report - am not going to resolve this issue at this time.
		#Find and count what keys exist - remove this later.
		#must be some tags with no 'k' so putting in workaround - may investigate more later.
		if 'k' in tag.attrib :
			if tag.attrib['k'] in keysDict.keys():
				keysDict[tag.attrib['k']] = keysDict[tag.attrib['k']] + 1
			else :
				keysDict[tag.attrib['k']] = 1
		'''	
		if (tag.tag == "member") :
			if "member" in node.keys() :
			#if list already exists, append to list   
				node["member"].append( { "ref" : check_problemchars(tag.attrib["ref"]), "role" : check_problemchars(tag.attrib["role"]), "type" : check_problemchars(tag.attrib["type"]) } )
			else :
				#else create "member" list 
				node["member"] = [ { "ref" : check_problemchars(tag.attrib["ref"]), "role" : check_problemchars(tag.attrib["role"]), "type" : check_problemchars(tag.attrib["type"]) } ]
		elif (tag.tag == "tag") :
			if isAddr(tag) :  
				if "address" in node.keys():
					#if dictionary already has an 'address' dictionary, update it
					node["address"].update(getAddrValue(tag))  #note - check for problem chars is done in this function for readability
				else :
					#else, create address dictionary
					node["address"] = getAddrValue(tag)
		else :
			'''
			Getting key error when running this - need to investigate.  Should only have "member" or "tag" elements so shouldn't be coming in here at all. 
			Seem to have a 'k' without a 'v'.
			
			Putting in workaround (basically ignoring) for now.
			
			later print out what elements are getting here and see if can spot problem
			'''
			if ('k' in element.attrib) and ('v' in element.attrib) :
				node[tag.attrib['k']] = check_problemchars(tag.attrib['v']) 
			
	return node
			
def cleanElement(element):
	
	
	if (element.tag == "node"):
		node = processNode(element)
		node["type"] = "node"
		return node
	elif (element.tag == "way"):
		node = processWay(element)
		node["type"] = "way"
		return node
	elif (element.tag == "relation"):
		node = processRelation(element)
		node["type"] = "relation"
		return node
	
	

def processMap(file_in, pretty = False):
    
    file_out = INTERMEDIATE_FILE.format(file_in)
    
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = cleanElement(element)
            if el:
                if pretty:
                    fo.write(json.dumps(el, indent=2)+",\n")
                else:
                    fo.write(json.dumps(el) + ",\n")

					

	
processMap(SOURCE_FILE, pretty = True)


print ('Total number of invalid nodes found : ', invalid_node_count)
print ('Total number of values with problem characters found : ', problemchar_count)

