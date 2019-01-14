'''
Reads in a JSON file and creates a mongodb database, then runs some queries on the database.
'''
import pprint
import json

from pymongo import MongoClient


INTERMEDIATE_FILE = 'dublin_tenth.json'
DB_NAME = 'dublinosm'
COLLECTION = "dublin"



#load data from file
with open(INTERMEDIATE_FILE) as f:
	data = json.loads(f.read())


#connect to mongo db
client = MongoClient('localhost:27017')
#connect to database - creates database if it does not exist.
dublinDB = client.DB_NAME
 

#before inserting, drop collection if it exists (i.e. a re-run)
if COLLECTION in dublinDB.collection_names():
    print ('Dropping collection: ', COLLECTION)
    dublinDB[COLLECTION].drop()
	
#insert data   
dublinDB.dublin.insert(data) 

    
#size of db
print('Number of records in database : ', dublinDB.dublin.count()) 

#number of unique users
print ('Number of unique users : ', len(dublinDB.dublin.distinct('user')))

    


#top three contributors
pipeline = [ { "$group" : { "_id" : "$user","count": {"$sum": 1 }}},
             { "$sort" : { "count" : -1 }},
             { "$limit" : 3 }
             ]
result = dublinDB.dublin.aggregate(pipeline)

print ('Top three contributors : ')    

for res in result:
	pprint.pprint(res)


#number of nodes and ways
print('Number of nodes : ', dublinDB.dublin.find({'type':'node'}).count())   
print('Number of ways : ', dublinDB.dublin.find({'type':'way'}).count())   
 
#number of pubs
print('Number of pubs : ', dublinDB.dublin.find({'amenity':'pub'}).count() )  
