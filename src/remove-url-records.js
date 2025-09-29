'use strict';
const MongoClient = require('mongodb').MongoClient;
const dbName = 'readability-database';
const client = new MongoClient('mongodb://localhost:27017')
const connection = client.connect()

connection.then(() => {
    const db = client.db(dbName);
    const collection = db.collection('documents');
    const url = 'https://rss.app/feeds/PVD9Pvei9yECJ8XV.xml'

    collection.deleteMany({origin:{$regex: `.*${url}.*`}}).then((result)=>{
        if(result && result.deletedCount){
            console.log(`Deleted ${result.deletedCount} documents`)
        } else {
            console.log('Nothing was deleted.')
        }
        client.close()
    })
})
