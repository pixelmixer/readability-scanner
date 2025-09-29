const moment = require('moment');

class DbOperations {
    constructor(client) {
        this.client = client;
        this.db = client.db('readability-database');
    }

    async aggregate(collection, pipeline) {
        try {
            const results = await this.db.collection(collection).aggregate(pipeline).toArray();
            return results;
        } catch (error) {
            throw error;
        }
    }

    async find(collection, query, options = {}) {
        try {
            const results = await this.db.collection(collection).find(query, options).toArray();
            return results;
        } catch (error) {
            throw error;
        }
    }
}

module.exports = DbOperations;