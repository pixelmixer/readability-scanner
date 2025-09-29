'use strict';
var path = require('path');
const dotenv = require('dotenv');
const cron = require('node-cron');
const cronstrue = require('cronstrue');
const Parser = require('rss-parser')
const feedParser = new Parser();
const fetch = require('node-fetch');
const express = require('express');
const striptags = require('striptags');
const MongoClient = require('mongodb').MongoClient;
const dbName = 'readability-database';
const querystring = require('querystring');
const normalizeWhitespace = require('normalize-html-whitespace');
const { URL } = require('url')
const excel = require('node-excel-export');
const { parse } = require('json2csv');
const moment = require('moment');
const expressLayouts = require('express-ejs-layouts')
const { htmlToText } = require('html-to-text');
const util = require('util')
const palette = require('google-palette')

const toxicity = require('@tensorflow-models/toxicity');
const { getOrigin,  } = require('./routeHandlers');



const smog = require('smog-formula')
const fleschKincaid = require('flesch-kincaid')
const flesch = require('flesch')
const daleChall = require('dale-chall-formula')
const gunningFog = require('gunning-fog')
const spache = require('spache-formula')
const automatedReadability = require('automated-readability')
const colemanLiau = require('coleman-liau')
const countable = require('countable')
const syllable = require('syllable')
dotenv.config()

const client = new MongoClient('mongodb://readability-database:27017')
const connection = client.connect()


const INTERVAL = process.env.INTERVAL;

// Constants
const PORT = 8080;
const HOST = '0.0.0.0';

// App
const app = express();

app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'ejs');
app.set('layout extractScripts', true)
app.set('layout extractStyles', true)
app.set('layout', 'layouts/layout');


app.use(expressLayouts)


app.listen(PORT, HOST);

console.log(`Running on http://${HOST}:${PORT}`);

const scanUrl = (req, res) => {
  return new Promise((resolve, reject) => {
    console.log('Requested', req.query.url)

    if (!req.query.url) {
      res.status(404).send('Please include a url to search: like: ?url=http://ap.com/article-name')
      reject('Please include a url to search: like: ?url=http://ap.com/article-name')
    }

    const body = { url: req.query.url };

    fetch('http://readability:3000', {
      method: 'post',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    })
      .then(res => res.json())
      .then(json => {
        if (json.content) {
          console.log(`Scanning 2 ${json.url}`)
          parseAndSaveResponse(json).then(response => {
            res.send(response)
            resolve(response)
          })

        } else {
          res.send('No content found in the page response')
          reject('No content found in the page response')
        }
      })
      .catch(err => {
        console.log(err);
        res.status(500).send(err)
      });
  })
}

const parseAndSaveResponse = (json) => {
  return new Promise((resolve, reject) => {
    console.log(`${new Date()} Parsing ${json.url}`)
    let cleanedContent = striptags(json.content, ['p'], ' ').replace(/\&nbsp;/g, '').replace(/<p[\s\S]*?>/g, '').replace(/<\/p>/g, '\r\n').trim()

    countable.count(cleanedContent, ({ paragraphs: paragraphs, sentences: sentence, words: word, characters: character }) => {
      const syllables = syllable(cleanedContent)
      const words = cleanedContent.split(' ')
      const wordSyllables = words.map(word => syllable(word))
      const avgWordSyllables = wordSyllables.reduce((prev, next) => prev + next) / wordSyllables.length
      const complexPolysillabicWord = wordSyllables.filter(count => count >= 3)
      // const paragraphs = cleanedContent.split('\r\n').filter(n=>n.length)


      json['paragraphs'] = paragraphs;
      json['words'] = word;
      json['sentences'] = sentence;
      json['characters'] = character;
      json['syllables'] = syllables;
      json['word syllables'] = avgWordSyllables;
      json['complex polysillabic words'] = complexPolysillabicWord.length

      json['Host'] = new URL(json.url).hostname
      json['Cleaned Data'] = cleanedContent;
      json['Smog'] = smog({ sentence, polysillabicWord: complexPolysillabicWord.length })
      json['Flesch'] = flesch({ sentence, word, syllable: syllables })
      json['Dale Chall'] = daleChall({ sentence, word })
      json['Dale Chall: Grade'] = daleChall.gradeLevel(json['Dale Chall'])
      json['Coleman Liau'] = colemanLiau({ sentence, word, letter: character })
      json['Flesch Kincaid'] = fleschKincaid({ sentence, word, syllable: syllables })
      json['Gunning Fog'] = gunningFog({ sentence, word, complexPolysillabicWord: complexPolysillabicWord.length })
      json['Spache'] = spache({ word, sentence })
      json['Automated Readability'] = automatedReadability({ sentence, word, character })
      json['date'] = new Date()

      // toxicity.load(0.9).then(model => {
      //   model.classify(sentence).then(predictions => {
      //     console.log(predictions)
      //   })
      // })

      connection.then(() => {
        const db = client.db(dbName);
        const collection = db.collection('documents');
        collection.replaceOne({ url: json.url }, json, { upsert: true })

        // const paragraphCounts = paragraphs.map((paragraph)=>{
        // 	const count = util.promisify(countable.count)
        // 	return count(paragraph)
        // })
        // console.log(paragraphCounts)
        // Promise.all(paragraphCounts).then((content)=>{
        // 	console.log(JSON.stringify(content, null, '	'))
        // })
        resolve(cleanedContent)
      })
    })
  })
}

const startCron = () => {
  if (cron.validate(INTERVAL)) {
    console.log(`Scheduling Notification for ${cronstrue.toString(INTERVAL)}`)

    cron.schedule(INTERVAL, () => {
      console.log('Running cron job')
      scanFeeds()
    })
  }

  const scanFeeds = () => {
    connection.then(() => {
      const db = client.db(dbName);
      const urlCollection = db.collection('urls');

      urlCollection.find({}).toArray((err, urls) => {
        const urlList = urls.map(({ url }) => url)
        console.log(`Monitoring ${urlList}`)

        if (err) {
          console.error(err);
          return
        }

        Promise.all(urlList.map(async (url) => {
          const feedData = await feedParser.parseURL(url);

          Promise.all(feedData.items.map(async (article) => {
            const { title, link, pubDate } = article;
            const body = { url: link };

            fetch('http://readability:3000', {
              method: 'post',
              body: JSON.stringify(body),
              headers: { 'Content-Type': 'application/json' },
            })
              .then(res => res.json())
              .then(json => {
                if (json.content) {
                  json['publication date'] = new Date(pubDate)
                  json['title'] = title
                  json['origin'] = url

                  parseAndSaveResponse(json)
                }
              })
          }))
        }));
      })
    })
  }

  scanFeeds()
}

const addUrl = (req, res) => {
  const url = req.query.url;
  return new Promise((resolve, reject) => {

    // TODO: Validate that its a proper rss feed before adding to the database.

    connection.then(() => {
      const db = client.db(dbName);
      const collection = db.collection('urls');
      const content = { url }
      collection.replaceOne(content, content, { upsert: true })

      console.log(`Saved url: ${url}`)
      res.send(content)
      resolve(content)
    })
  })
}

const exportToCSV = (req, res) => {
  const type = req.query.type;

  connection.then(() => {
    const db = client.db(dbName);
    const collection = db.collection('documents');
    // const aggregate = [
    //   {
    //     '$match': {
    //       'publication date': {
    //         '$gte': new Date('Mon, 29 Mar 2021 04:00:00 GMT'),
    //         '$lte': new Date('Mon, 05 Apr 2021 03:59:59 GMT')
    //       },
    //       'origin': {
    //         '$ne': null
    //       }
    //     }
    //   }, {
    //     '$project': {
    //       'url': '$url',
    //       'Host': '$Host',
    //       'publication date': '$publication date'
    //     }
    //   }
    // ];

    const aggregate = [
      {
        '$group': {
          '_id': "$Host",
          "words": { '$avg': "$words" },
          "sentences": { '$avg': "$sentences" },
          "paragraphs": { '$avg': "$paragraphs" },
          "characters": { '$avg': "$characters" },
          "syllables": { '$avg': "$syllables" },
          "word syllables": { '$avg': "$word syllables" },
          "complex polysillabic words": { '$avg': "$complex polysillabic words" },
          "Flesch": { '$avg': "$Flesch" },
          "Flesch Kincaid": { '$avg': "$Flesch Kincaid" },
          "Smog": { '$avg': "$Smog" },
          "Dale Chall": { '$avg': "$Dale Chall" },
          "Coleman Liau": { '$avg': "$Coleman Liau" },
          "Gunning Fog": { '$avg': "$Gunning Fog" },
          "Spache": { '$avg': "$Spache" },
          "Automated Readability": { '$avg': "$Automated Readability" },
          "origin": { '$first': "$origin" },
          "articles": { $sum: 1 }
        }
      }, {
        '$match': {
          '_id': {
            '$ne': null
          },
          "articles": { $gte: 100 }
        }
      }, {
        '$sort': {
          'date': -1
        }
      }
    ]

    collection.aggregate(aggregate).toArray(function (err, items) {
      if (err) {
        res.send(err);
      } else {
        console.log(items);

        if (type === 'json') {
          res.json(items)
        } else {
          res.attachment('report.csv')
          res.send(parse(items))
        }
      }
    })
  })
}

const filterDaily = (start, end) => {
  return new Promise((resolve, reject) => {
    /*
    * Requires the MongoDB Node.js Driver
    * https://mongodb.github.io/node-mongodb-native
    */

    const agg = [
      {
        '$match': {
          'publication date': {
            '$lte': end,
            '$gte': start
          },
          'origin': {
            '$ne': null,
          }
        }
      },
      {
        '$group': {
          '_id': "$Host",
          "words": { '$avg': "$words" },
          "sentences": { '$avg': "$sentences" },
          "paragraphs": { '$avg': "$paragraphs" },
          "characters": { '$avg': "$characters" },
          "syllables": { '$avg': "$syllables" },
          "word syllables": { '$avg': "$word syllables" },
          "complex polysillabic words": { '$avg': "$complex polysillabic words" },
          "Flesch": { '$avg': "$Flesch" },
          "Flesch Kincaid": { '$avg': "$Flesch Kincaid" },
          "Smog": { '$avg': "$Smog" },
          "Dale Chall": { '$avg': "$Dale Chall" },
          "Coleman Liau": { '$avg': "$Coleman Liau" },
          "Gunning Fog": { '$avg': "$Gunning Fog" },
          "Spache": { '$avg': "$Spache" },
          "Automated Readability": { '$avg': "$Automated Readability" },
          "origin": { '$first': "$origin" },
          "articles": { $sum: 1 }
        }
      },
      {
        "$match": {
          "articles": { $gte: 1 }
        }
      },
      {
        '$sort': {
          'bias': 1
        }
      },
      {
        '$lookup': {
          'from': 'urls',
          'localField': 'origin',
          'foreignField': 'url',
          'as': 'host'
        }
      },
      {
        '$replaceRoot': {
          'newRoot': {
            '$mergeObjects': [
              {
                '$arrayElemAt': [
                  '$host', 0
                ]
              }, '$$ROOT'
            ]
          }
        }
      },
      {
        '$project': {
          'host': 0
        }
      },
      {
        '$sort': {
          'Flesch': -1
        }
      }
    ];

    connection.then(() => {
      const coll = client.db('readability-database').collection('documents');
      coll.aggregate(agg).toArray((err, result) => {
        if (err) {
          reject(err)
        } else {
          resolve(result)
        }
      });
    }, (err) => {
      reject(err)
    })
  })
}

const getGraph = (req, res) => {
  const requestedJson = req.query.format === 'json'
  const days = req.query.days || 20
  const format = 'MM/DD/YY HH:mm'

  const end = req.query.end ? moment(new Date(decodeURIComponent(req.query.end))) : moment()
  const start = req.query.start ? moment(new Date(decodeURIComponent(req.query.start))) : moment(end).subtract(days, 'days')
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

  let promises = []
  let dateList = []

  let previousDate = start

  for (let i = 0; i < duration; i++) {
    const promiseStart = moment(previousDate).add(1, 'days')
    const promiseEnd = moment(promiseStart).add(1, 'days')

    previousDate = promiseStart

    console.log(promiseStart.format(format), promiseEnd.format(format))
    dateList = [...dateList, promiseStart.format(format)]
    promises = [filterDaily(promiseStart.toDate(), promiseEnd.toDate()), ...promises]
  }

  Promise.all(promises).then((results) => {
    const idList = {
    }
    results.forEach((result) => {
      result.forEach((group_result) => {
        const groupId = group_result.name
        const id = idList[groupId]

        if (!id) {
          idList[groupId] = {
            label: groupId,
            fill: false,
            tension: 0.1,
            data: [
              // group_result['Flesch'],
              group_result['Flesch'],
              // group_result['paragraphs']
            ],
            borderColor: palette('qualitative', result.length).map(function (hex) {
              return '#' + hex;
            })
          }
        } else {
          idList[groupId].data = [
            ...idList[groupId].data,
            // group_result['Flesch'],
            group_result['Flesch'],
            // group_result['paragraphs']
          ]
        }
      })
    })

    if (requestedJson) {
      res.json({ days: duration, data: Object.values(idList) })
    } else {
      res.render('pages/graph', { results: { days: duration, data: Object.values(idList) }, dateList: dateList, dates: dates, title: 'Daily News Readability Report' })
    }
  },
    (err) => {
      console.error(err)
      res.status(400).send(err)
    })
}

const getDaily = (req, res) => {
  const requestedJson = req.query.format === 'json'
  const format = 'MM/DD/YY HH:mm'

  const end = req.query.end ? moment(new Date(decodeURIComponent(req.query.end))) : moment()
  const start = req.query.start ? moment(new Date(decodeURIComponent(req.query.start))) : moment(end).subtract(7, 'days')
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

  // if (formattedStart !== 'Invalid date' && formattedEnd !== 'Invalid date') {
  console.log(dates)
  filterDaily(start.toDate(), end.toDate()).then((results) => {
    if (requestedJson) {
      res.json(results)
    } else {
      res.render('pages/daily', { results, dates: dates, title: 'Daily News Readability Report' })
    }
  },
    (err) => {
      console.error(err)
      res.status(400).send(err)
    })
  // } else {


  // 	if (formattedStart === 'Invalid date' && formattedEnd === 'Invalid date') {
  // 		const endDate = moment()
  // 		const startDate = moment(endDate).subtract(1, 'week')

  // 		const helpMessage = `${req.path}?start=${startDate.format(format)}&end=${endDate.format(format)}`
  // 		res.status(400).json({ error: `Please provide valid dates like: ${helpMessage}` })
  // 	}
  // }
}

app.route('/source/:origin').get(getOrigin);
app.route('/daily').get(getDaily);
app.route('/graph').get(getGraph);
app.route('/export').get(exportToCSV)
app.route('/add-url').get(addUrl);
app.route('/').get(scanUrl);


startCron()