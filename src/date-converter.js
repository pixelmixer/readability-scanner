'use strict';
const MongoClient = require('mongodb').MongoClient;
const dbName = 'readability-database';
const client = new MongoClient('mongodb://localhost:27017')
const connection = client.connect()

connection.then(() => {
    const db = client.db(dbName);
    const collection = db.collection('documents');

    collection.find({}).toArray((err, documents)=>{
        documents.forEach((document)=>{
            if(typeof document['publication date'] === 'string'){
                console.log(`converting ${document['publication date']} to ${new Date(document['publication date'])}`)
                document['publication date'] = new Date(document['publication date'])
                collection.replaceOne({url: document.url}, document, {upsert: true})
            } else {
                console.log(`${document['publication date']} is already ${typeof document['publication date']}`)
            }
        })
    })
})
