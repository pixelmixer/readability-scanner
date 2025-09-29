// const MongoClient = require('mongodb').MongoClient;
// const dbName = 'readability-database';
const moment = require('moment');
// const client = new MongoClient('mongodb://localhost:27017')
// const ReadabilityAnalysis = require('./readabilityAnalysis');
// const DbOperations = require('./dbOperations');
// Assume `client` is your MongoDB client from a successfully connected database instance

// const dbOperations = new DbOperations(client);
// const analysis = new ReadabilityAnalysis(dbOperations);

async function getOrigin(req, res) {
    // Your adapted `getOrigin` logic here, calling analysis.getOriginData()
    const requestedJson = req.query.format === 'json'
    const origin = req.params.origin;
    const format = 'MM/DD/YY HH:mm'
    const start = moment(new Date(decodeURIComponent(req.query.start)))
    const end = moment(new Date(decodeURIComponent(req.query.end)))


    // analysis.getOriginData(origin, start, end, requestedJson)

    const formattedStart = start.format(format)
    const formattedEnd = end.format(format)

    const diff = end.diff(start)
    const previous = moment(start).subtract(diff).format(format)
    const next = moment(end).add(diff).format(format)
    const duration = moment.duration(diff).get('days')

    const dates = {
        formattedStart,
        formattedEnd,
        previous,
        next,
        duration
    }

    if (formattedStart !== 'Invalid date' && formattedEnd !== 'Invalid date') {
        console.log(dates)
        connection.then(() => {
            const coll = client.db('readability-database').collection('documents');
            coll.find({
                "Host": origin,
                "publication date": {
                    $lte: end.toDate(),
                    $gte: start.toDate()
                },
            }, {
                sort: {
                    "publication date": -1
                }
            }).toArray((err, results) => {
                if (err) {
                    res.status(400).json(err)
                } else {
                    if (requestedJson) {
                        res.json(results)
                    } else {
                        res.render('pages/origin', { results, dates: dates, title: `Readbility report for ${origin}` })
                    }
                }
            });
        }, (err) => {
            res.status(400).json(err)
        })
    } else {
        const endDate = moment()
        const startDate = moment(endDate).subtract(1, 'week')

        const helpMessage = `${req.path}?start=${startDate.format(format)}&end=${endDate.format(format)}`
        res.status(400).json({ error: `Please provide valid dates like: ${helpMessage}` })
    }
}

// async function getDaily(req, res) {
//     // Your adapted `getDaily` logic here, calling analysis.getDailyData()
// }

// async function getGraph(req, res) {
//     // Your adapted `getGraph` logic here, calling analysis.getGraphData()
// }

module.exports = {
    getOrigin,
    // getDaily,
    // getGraph,
};