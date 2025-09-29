const DbOperations = require('./dbOperations');

class ReadabilityAnalysis {
    constructor(dbOperations) {
        this.dbOperations = dbOperations;
    }

    // async filterDaily(start, end) {
    //     // Logic adapted from `filterDaily`, utilizing the DbOperations class
    //     return new Promise((resolve, reject) => {
    //         /*
    //         * Requires the MongoDB Node.js Driver
    //         * https://mongodb.github.io/node-mongodb-native
    //         */

    //         const agg = [
    //             {
    //                 '$match': {
    //                     'publication date': {
    //                         '$lte': end,
    //                         '$gte': start
    //                     },
    //                     'origin': {
    //                         '$ne': null,
    //                     }
    //                 }
    //             },
    //             {
    //                 '$group': {
    //                     '_id': "$Host",
    //                     "words": { '$avg': "$words" },
    //                     "sentences": { '$avg': "$sentences" },
    //                     "paragraphs": { '$avg': "$paragraphs" },
    //                     "characters": { '$avg': "$characters" },
    //                     "syllables": { '$avg': "$syllables" },
    //                     "word syllables": { '$avg': "$word syllables" },
    //                     "complex polysillabic words": { '$avg': "$complex polysillabic words" },
    //                     "Flesch": { '$avg': "$Flesch" },
    //                     "Flesch Kincaid": { '$avg': "$Flesch Kincaid" },
    //                     "Smog": { '$avg': "$Smog" },
    //                     "Dale Chall": { '$avg': "$Dale Chall" },
    //                     "Coleman Liau": { '$avg': "$Coleman Liau" },
    //                     "Gunning Fog": { '$avg': "$Gunning Fog" },
    //                     "Spache": { '$avg': "$Spache" },
    //                     "Automated Readability": { '$avg': "$Automated Readability" },
    //                     "origin": { '$first': "$origin" },
    //                     "articles": { $sum: 1 }
    //                 }
    //             },
    //             {
    //                 "$match": {
    //                     "articles": { $gte: 1 }
    //                 }
    //             },
    //             {
    //                 '$sort': {
    //                     'bias': 1
    //                 }
    //             },
    //             {
    //                 '$lookup': {
    //                     'from': 'urls',
    //                     'localField': 'origin',
    //                     'foreignField': 'url',
    //                     'as': 'host'
    //                 }
    //             },
    //             {
    //                 '$replaceRoot': {
    //                     'newRoot': {
    //                         '$mergeObjects': [
    //                             {
    //                                 '$arrayElemAt': [
    //                                     '$host', 0
    //                                 ]
    //                             }, '$$ROOT'
    //                         ]
    //                     }
    //                 }
    //             },
    //             {
    //                 '$project': {
    //                     'host': 0
    //                 }
    //             },
    //             {
    //                 '$sort': {
    //                     'Flesch': -1
    //                 }
    //             }
    //         ];

    //         connection.then(() => {
    //             const coll = client.db('readability-database').collection('documents');
    //             coll.aggregate(agg).toArray((err, result) => {
    //                 if (err) {
    //                     reject(err)
    //                 } else {
    //                     resolve(result)
    //                 }
    //             });
    //         }, (err) => {
    //             reject(err)
    //         })
    //     })
    // }

    // async getGraphData(start, end, duration) {
    //     // Adapt `getGraph` logic here
    //     const requestedJson = req.query.format === 'json'
    //     const days = req.query.days || 20
    //     const format = 'MM/DD/YY HH:mm'

    //     const end = req.query.end ? moment(new Date(decodeURIComponent(req.query.end))) : moment()
    //     const start = req.query.start ? moment(new Date(decodeURIComponent(req.query.start))) : moment(end).subtract(days, 'days')
    //     const formattedStart = start.format(format)
    //     const formattedEnd = end.format(format)

    //     const diff = end.diff(start)
    //     const previous = moment(start).subtract(diff).format(format)
    //     const next = moment(end).add(diff).format(format)
    //     const duration = moment.duration(diff).get('days')

    //     const dates = {
    //         formattedStart,
    //         formattedEnd,
    //         previous,
    //         next,
    //         duration
    //     }

    //     let promises = []
    //     let dateList = []

    //     let previousDate = start

    //     for (let i = 0; i < duration; i++) {
    //         const promiseStart = moment(previousDate).add(1, 'days')
    //         const promiseEnd = moment(promiseStart).add(1, 'days')

    //         previousDate = promiseStart

    //         console.log(promiseStart.format(format), promiseEnd.format(format))
    //         dateList = [...dateList, promiseStart.format(format)]
    //         promises = [filterDaily(promiseStart.toDate(), promiseEnd.toDate()), ...promises]
    //     }

    //     Promise.all(promises).then((results) => {
    //         const idList = {
    //         }
    //         results.forEach((result) => {
    //             result.forEach((group_result) => {
    //                 const groupId = group_result.name
    //                 const id = idList[groupId]

    //                 if (!id) {
    //                     idList[groupId] = {
    //                         label: groupId,
    //                         fill: false,
    //                         tension: 0.1,
    //                         data: [
    //                             // group_result['Flesch'],
    //                             group_result['Flesch'],
    //                             // group_result['paragraphs']
    //                         ],
    //                         borderColor: palette('qualitative', result.length).map(function (hex) {
    //                             return '#' + hex;
    //                         })
    //                     }
    //                 } else {
    //                     idList[groupId].data = [
    //                         ...idList[groupId].data,
    //                         // group_result['Flesch'],
    //                         group_result['Flesch'],
    //                         // group_result['paragraphs']
    //                     ]
    //                 }
    //             })
    //         })

    //         if (requestedJson) {
    //             res.json({ days: duration, data: Object.values(idList) })
    //         } else {
    //             res.render('pages/graph', { results: { days: duration, data: Object.values(idList) }, dateList: dateList, dates: dates, title: 'Daily News Readability Report' })
    //         }
    //     },
    //         (err) => {
    //             console.error(err)
    //             res.status(400).send(err)
    //         })
    // }

    // async getDailyData(start, end, format) {
    //     // Adapt `getDaily` logic here
    //     const requestedJson = format === 'json'
    //     const dateFormat = 'MM/DD/YY HH:mm'

    //     const endDate = req.query.end ? moment(new Date(decodeURIComponent(req.query.end))) : moment()
    //     const start = req.query.start ? moment(new Date(decodeURIComponent(req.query.start))) : moment(endDate).subtract(7, 'days')
    //     const formattedStart = start.format(dateFormat)
    //     const formattedEnd = endDate.format(dateFormat)

    //     const diff = endDate.diff(start)
    //     const previous = moment(start).subtract(diff).format(dateFormat)
    //     const next = moment(endDate).add(diff).format(dateFormat)
    //     const duration = moment.duration(diff).get('days')

    //     const dates = {
    //         formattedStart,
    //         formattedEnd,
    //         previous,
    //         next,
    //         duration
    //     }

    //     // if (formattedStart !== 'Invalid date' && formattedEnd !== 'Invalid date') {
    //     console.log(dates)
    //     filterDaily(start.toDate(), endDate.toDate()).then((results) => {
    //         if (requestedJson) {
    //             res.json(results)
    //         } else {
    //             res.render('pages/daily', { results, dates: dates, title: 'Daily News Readability Report' })
    //         }
    //     },
    //         (err) => {
    //             console.error(err)
    //             res.status(400).send(err)
    //         })
    //     // } else {


    //     // 	if (formattedStart === 'Invalid date' && formattedEnd === 'Invalid date') {
    //     // 		const endDate = moment()
    //     // 		const startDate = moment(endDate).subtract(1, 'week')

    //     // 		const helpMessage = `${req.path}?start=${startDate.format(format)}&end=${endDate.format(format)}`
    //     // 		res.status(400).json({ error: `Please provide valid dates like: ${helpMessage}` })
    //     // 	}
    //     // }
    // }

    async getOriginData(origin, start, end, requestedJson) {
        // Adapt `getOrigin` logic here
        const format = 'MM/DD/YY HH:mm'

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
}

module.exports = ReadabilityAnalysis;