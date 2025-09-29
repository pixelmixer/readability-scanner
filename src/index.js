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
const { getOrigin, } = require('./routeHandlers');



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

// User agents for rotation to avoid bot detection
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
];

// Get a random user agent
const getRandomUserAgent = () => {
  return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
};

const client = new MongoClient('mongodb://readability-database:27017', {
  useUnifiedTopology: true,
  useNewUrlParser: true
})
const connection = client.connect()

// Build/startup timestamp for cache-busting verification
const BUILD_TIMESTAMP = new Date().toISOString();
const BUILD_VERSION = `v1.0.0-${Date.now()}`;

console.log(`🚀 News Analysis System started at: ${BUILD_TIMESTAMP}`);
console.log(`📦 Build Version: ${BUILD_VERSION}`);

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
app.use(express.urlencoded({ extended: true }))
app.use(express.json())


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
    try {
      console.log(`${new Date()} Parsing ${json.url}`)
      let cleanedContent = striptags(json.content, ['p'], ' ').replace(/\&nbsp;/g, '').replace(/<p[\s\S]*?>/g, '').replace(/<\/p>/g, '\r\n').trim()

      countable.count(cleanedContent, ({ paragraphs: paragraphs, sentences: sentence, words: word, characters: character }) => {
        try {
          const syllables = syllable(cleanedContent)
          const words = cleanedContent.split(' ')
          const wordSyllables = words.map(word => syllable(word))
          const avgWordSyllables = wordSyllables.reduce((prev, next) => prev + next) / wordSyllables.length
          const complexPolysillabicWord = wordSyllables.filter(count => count >= 3)

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

          connection.then(() => {
            const db = client.db(dbName);
            const collection = db.collection('documents');
            collection.replaceOne({ url: json.url }, json, { upsert: true })
              .then(() => resolve(cleanedContent))
              .catch(err => {
                console.error('Error saving to database:', err);
                reject(err);
              });
          }).catch(err => {
            console.error('Database connection error:', err);
            reject(err);
          });
        } catch (analysisError) {
          console.error('Error in readability analysis:', analysisError);
          reject(analysisError);
        }
      });
    } catch (error) {
      console.error('Error in parseAndSaveResponse:', error);
      reject(error);
    }
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

  const scanFeeds = async () => {
    try {
      await connection;
      const db = client.db(dbName);
      const urlCollection = db.collection('urls');

      const urls = await urlCollection.find({}).toArray();
      const urlList = urls.map(({ url }) => url);
      console.log(`Monitoring ${urlList}`);

      if (urlList.length === 0) {
        console.log('No URLs configured for monitoring');
        return;
      }

      await Promise.all(urlList.map(async (url) => {
        try {
          const result = await scanSingleSource(url);
          if (result.failed && result.failed > 0) {
            const failureRate = Math.round((result.failed / result.total) * 100);
            console.log(`Cron scan completed for ${url}: ${result.scanned}/${result.total} articles processed (${result.failed} failed, ${failureRate}% failure rate)`);

            if (failureRate > 75) {
              console.warn(`⚠️  High failure rate for ${url} during cron scan. Consider reviewing this source.`);
            }
          } else {
            console.log(`✅ Cron scan completed for ${url}: ${result.scanned}/${result.total} articles processed successfully`);
          }
        } catch (error) {
          console.error(`Error scanning ${url} during cron job:`, error.message);
        }
      }));
    } catch (error) {
      console.error('Error in scanFeeds:', error);
    }
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

// Single Source Scanning Function
const scanSingleSource = async (sourceUrl) => {
  return new Promise(async (resolve, reject) => {
    try {
      console.log(`Starting immediate scan of: ${sourceUrl}`);

      // Validate URL before attempting to parse
      try {
        new URL(sourceUrl);
      } catch (urlError) {
        console.error(`Invalid URL format: ${sourceUrl}`);
        resolve({ scanned: 0, total: 0, source: sourceUrl, error: 'Invalid URL format' });
        return;
      }

      const feedData = await feedParser.parseURL(sourceUrl);

      if (!feedData.items || feedData.items.length === 0) {
        console.log(`No articles found in feed: ${sourceUrl}`);
        resolve({ scanned: 0, total: 0, source: sourceUrl });
        return;
      }

      console.log(`Found ${feedData.items.length} articles in ${sourceUrl}`);

      // Initialize failure tracking for this scan
      const failureStats = {
        total: feedData.items.length,
        http500: 0,
        http403: 0,
        http429: 0,
        timeout: 0,
        noContent: 0,
        other: 0
      };

      // Process articles with rate limiting and retry logic
      const scanPromises = feedData.items.map(async (article, index) => {
        try {
          const { title, link, pubDate } = article;

          if (!link) {
            console.warn(`Article missing link, skipping: ${title}`);
            return false;
          }

          // Add delay between requests to avoid overwhelming the readability service
          if (index > 0) {
            await new Promise(resolve => setTimeout(resolve, 100 * Math.floor(index / 5))); // 100ms delay every 5 articles
          }

          let attempts = 0;
          const maxAttempts = 2;

          while (attempts < maxAttempts) {
            try {
              console.log(`🔍 Processing article ${index + 1}/${feedData.items.length}: ${link.substring(0, 80)}...`);

              // Use rotating user agents to avoid detection
              const userAgent = getRandomUserAgent();
              const requestBody = {
                url: link,
                // Add user agent to the request body for the readability service
                headers: {
                  'User-Agent': userAgent
                }
              };

              console.log(`🕵️ Using User-Agent: ${userAgent.substring(0, 50)}...`);

              const response = await fetch('http://readability:3000', {
                method: 'post',
                body: JSON.stringify(requestBody),
                headers: {
                  'Content-Type': 'application/json',
                  'User-Agent': 'NewsAnalysis-Scanner/1.0'
                },
                timeout: 30000 // 30 second timeout
              });

              // Enhanced logging for response analysis
              console.log(`📡 HTTP Response: ${response.status} ${response.statusText} for ${link}`);

              if (!response.ok) {
                // Capture response details for analysis
                let responseText = '';
                try {
                  responseText = await response.text();
                } catch (textError) {
                  console.warn(`Could not read response text: ${textError.message}`);
                }

                // Log response headers for debugging
                const headers = {};
                response.headers.forEach((value, key) => {
                  headers[key] = value;
                });

                console.error(`❌ HTTP ${response.status} Error Details:`);
                console.error(`   URL: ${link}`);
                console.error(`   Status: ${response.status} ${response.statusText}`);
                console.error(`   Headers:`, JSON.stringify(headers, null, 2));

                // Log first 500 chars of response for error analysis
                if (responseText) {
                  const truncatedResponse = responseText.substring(0, 500);
                  console.error(`   Response Body (first 500 chars): ${truncatedResponse}`);

                  // Detect common blocking patterns
                  const lowerResponse = responseText.toLowerCase();
                  if (lowerResponse.includes('rate limit') || lowerResponse.includes('too many requests')) {
                    console.warn(`🚫 RATE LIMITING detected for ${link}`);
                  }
                  if (lowerResponse.includes('blocked') || lowerResponse.includes('forbidden')) {
                    console.warn(`🚫 ACCESS BLOCKED detected for ${link}`);
                  }
                  if (lowerResponse.includes('robot') || lowerResponse.includes('bot')) {
                    console.warn(`🤖 BOT DETECTION detected for ${link}`);
                  }
                  if (lowerResponse.includes('captcha') || lowerResponse.includes('verify')) {
                    console.warn(`🔐 CAPTCHA/VERIFICATION detected for ${link}`);
                  }
                  if (lowerResponse.includes('cloudflare') || lowerResponse.includes('ddos')) {
                    console.warn(`☁️ CLOUDFLARE/DDOS PROTECTION detected for ${link}`);
                  }
                }

                if (response.status >= 500 && attempts < maxAttempts - 1) {
                  // Retry on server errors
                  attempts++;
                  console.warn(`🔄 Retrying HTTP ${response.status} for ${link} (attempt ${attempts}/${maxAttempts})`);
                  await new Promise(resolve => setTimeout(resolve, 1000 * attempts)); // Exponential backoff
                  continue;
                } else if (response.status === 429) {
                  // Special handling for rate limiting
                  failureStats.http429++;
                  const retryAfter = response.headers.get('retry-after') || (attempts * 5);
                  console.warn(`⏳ Rate limited! Waiting ${retryAfter} seconds before retry...`);
                  await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
                  if (attempts < maxAttempts - 1) {
                    attempts++;
                    continue;
                  }
                } else if (response.status === 403 || response.status === 401) {
                  failureStats.http403++;
                  console.warn(`🚫 Access denied (${response.status}) - likely bot detection or authentication required`);
                  throw new Error(`HTTP ${response.status}: ${response.statusText} - Access denied`);
                } else if (response.status >= 500) {
                  failureStats.http500++;
                  throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                } else {
                  failureStats.other++;
                  throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
              }

              const json = await response.json();
              console.log(`✅ Successfully extracted content from: ${link}`);

              if (json.content) {
                json['publication date'] = new Date(pubDate);
                json['title'] = title;
                json['origin'] = sourceUrl;

                await parseAndSaveResponse(json);
                return true;
              } else {
                failureStats.noContent++;
                console.warn(`⚠️ No content extracted from readability service for: ${link}`);
                return false;
              }
            } catch (requestError) {
              attempts++;
              console.error(`💥 Request failed for ${link} (attempt ${attempts}/${maxAttempts}): ${requestError.message}`);

              if (attempts >= maxAttempts) {
                console.error(`🔴 Max attempts reached for ${link}. Final error: ${requestError.message}`);
                throw requestError;
              } else {
                console.warn(`🔄 Retrying in ${1000 * attempts}ms...`);
                await new Promise(resolve => setTimeout(resolve, 1000 * attempts)); // Exponential backoff
              }
            }
          }

          return false;
        } catch (articleError) {
          console.error(`Error processing article ${article.link || 'unknown'}:`, articleError.message);
          return false;
        }
      });

      const results = await Promise.all(scanPromises);
      const successCount = results.filter(Boolean).length;
      const failedCount = feedData.items.length - successCount;

      // Log detailed failure statistics
      if (failedCount > 0) {
        const failureRate = Math.round((failedCount / feedData.items.length) * 100);
        console.log(`📊 Scan Results for ${sourceUrl}:`);
        console.log(`   ✅ Success: ${successCount}/${feedData.items.length} (${100 - failureRate}%)`);
        console.log(`   ❌ Failed: ${failedCount}/${feedData.items.length} (${failureRate}%)`);
        console.log(`   📈 Failure Breakdown:`);
        if (failureStats.http500 > 0) console.log(`      🔴 HTTP 5xx errors: ${failureStats.http500}`);
        if (failureStats.http403 > 0) console.log(`      🚫 HTTP 403/401 (blocked): ${failureStats.http403}`);
        if (failureStats.http429 > 0) console.log(`      ⏳ HTTP 429 (rate limited): ${failureStats.http429}`);
        if (failureStats.noContent > 0) console.log(`      📄 No content extracted: ${failureStats.noContent}`);
        if (failureStats.other > 0) console.log(`      ❓ Other errors: ${failureStats.other}`);

        // Provide actionable insights
        if (failureStats.http403 > failedCount * 0.5) {
          console.warn(`🤖 DIAGNOSIS: High number of 403 errors suggests bot detection. Consider user-agent rotation.`);
        }
        if (failureStats.http429 > failedCount * 0.3) {
          console.warn(`⏳ DIAGNOSIS: Rate limiting detected. Consider slower request timing.`);
        }
        if (failureStats.http500 > failedCount * 0.7) {
          console.warn(`💥 DIAGNOSIS: High server errors. Readability service may be struggling with this site's content.`);
        }
        if (failureStats.noContent > failedCount * 0.8) {
          console.warn(`📰 DIAGNOSIS: High 'no content' rate suggests redirect URLs or paywall protection.`);
          if (sourceUrl.includes('google') || sourceUrl.includes('news.google')) {
            console.warn(`🔗 Google News feeds often contain redirect URLs that don't extract well. Consider direct publisher feeds.`);
          }
        }

        if (failureRate > 75) {
          console.warn(`⚠️  High failure rate for ${sourceUrl}. This source may have anti-bot protection or content structure issues.`);
        }
      } else {
        console.log(`✅ Completed scan of ${sourceUrl}: ${successCount}/${feedData.items.length} articles processed successfully`);
      }

      resolve({
        scanned: successCount,
        total: feedData.items.length,
        failed: failedCount,
        source: sourceUrl
      });

    } catch (error) {
      console.error(`Error scanning source ${sourceUrl}:`, error.message);
      // Don't reject, resolve with error info instead to prevent unhandled promise rejections
      resolve({ scanned: 0, total: 0, source: sourceUrl, error: error.message });
    }
  });
};

// Source Management Functions
const getSources = async (req, res) => {
  try {
    await connection;
    const db = client.db(dbName);

    // Get all sources
    const urlCollection = db.collection('urls');
    const sources = await urlCollection.find({}).toArray();

    // Get article counts for each source
    const documentCollection = db.collection('documents');
    const sourcesWithCounts = await Promise.all(sources.map(async (source) => {
      const count = await documentCollection.countDocuments({ origin: source.url });
      const latestArticle = await documentCollection.findOne(
        { origin: source.url },
        { sort: { 'publication date': -1 } }
      );

      return {
        ...source,
        articleCount: count,
        lastFetched: latestArticle ? latestArticle['publication date'] : null,
        name: source.name || new URL(source.url).hostname
      };
    }));

    res.render('pages/sources', {
      sources: sourcesWithCounts,
      title: 'News Sources Management',
      buildTimestamp: BUILD_TIMESTAMP,
      buildVersion: BUILD_VERSION
    });
  } catch (error) {
    console.error('Error fetching sources:', error);
    res.status(500).send('Error fetching sources');
  }
}

const addSource = async (req, res) => {
  try {
    const { url, name, description } = req.body;

    if (!url) {
      return res.status(400).send('URL is required');
    }

    // Validate URL format
    try {
      new URL(url);
    } catch (urlError) {
      return res.status(400).send('Invalid URL format');
    }

    // Basic RSS feed validation
    const urlLower = url.toLowerCase();
    const isLikelyAPI = urlLower.includes('/api/') ||
      urlLower.includes('json') ||
      urlLower.includes('.json') ||
      urlLower.includes('format=json');

    if (isLikelyAPI) {
      return res.status(400).send('This appears to be an API endpoint, not an RSS feed. Please use an RSS feed URL (usually ending in .xml, .rss, or containing "rss" or "feed")');
    }

    // Validate that it's actually an RSS feed by testing it
    try {
      console.log(`Validating RSS feed: ${url}`);
      const testFeed = await feedParser.parseURL(url);

      if (!testFeed || !testFeed.title) {
        return res.status(400).send('Unable to parse this URL as an RSS feed. Please verify it\'s a valid RSS/XML feed.');
      }

      console.log(`RSS feed validation successful: ${testFeed.title}`);
    } catch (feedError) {
      console.error(`RSS validation failed for ${url}:`, feedError.message);
      return res.status(400).send(`RSS feed validation failed: ${feedError.message}. Please check that this is a valid RSS feed URL.`);
    }

    await connection;
    const db = client.db(dbName);
    const collection = db.collection('urls');

    const sourceData = {
      url,
      name: name || new URL(url).hostname,
      description: description || '',
      dateAdded: new Date()
    };

    await collection.replaceOne({ url }, sourceData, { upsert: true });

    console.log(`Added source: ${url}`);

    // Start immediate scan of the new source
    scanSingleSource(url)
      .then(result => {
        if (result.failed && result.failed > 0) {
          const failureRate = Math.round((result.failed / result.total) * 100);
          console.log(`Immediate scan completed for new source: ${result.scanned}/${result.total} articles processed (${result.failed} failed, ${failureRate}% failure rate)`);

          if (failureRate > 50) {
            console.warn(`⚠️  New source ${url} has high failure rate. Consider checking if this source has anti-bot protection.`);
          }
        } else {
          console.log(`✅ Immediate scan completed for new source: ${result.scanned}/${result.total} articles processed successfully`);
        }
      })
      .catch(error => {
        console.error(`Immediate scan failed for new source ${url}:`, error);
      });

    res.redirect('/sources');
  } catch (error) {
    console.error('Error adding source:', error);
    res.status(500).send('Error adding source');
  }
}

const editSource = async (req, res) => {
  try {
    const { id } = req.params;
    const { url, name, description } = req.body;

    if (!url) {
      return res.status(400).send('URL is required');
    }

    await connection;
    const db = client.db(dbName);
    const collection = db.collection('urls');

    // Get the old source to check if URL changed
    const oldSource = await collection.findOne({ _id: require('mongodb').ObjectId(id) });
    const urlChanged = oldSource && oldSource.url !== url;

    const updateData = {
      url,
      name: name || new URL(url).hostname,
      description: description || '',
      lastModified: new Date()
    };

    await collection.updateOne({ _id: require('mongodb').ObjectId(id) }, { $set: updateData });

    console.log(`Updated source: ${id}`);

    // Start immediate scan if URL was changed or force scan for any edit
    scanSingleSource(url)
      .then(result => {
        const scanReason = urlChanged ? 'URL changed' : 'source updated';
        if (result.failed && result.failed > 0) {
          const failureRate = Math.round((result.failed / result.total) * 100);
          console.log(`Immediate scan completed for edited source (${scanReason}): ${result.scanned}/${result.total} articles processed (${result.failed} failed, ${failureRate}% failure rate)`);
        } else {
          console.log(`✅ Immediate scan completed for edited source (${scanReason}): ${result.scanned}/${result.total} articles processed successfully`);
        }
      })
      .catch(error => {
        console.error(`Immediate scan failed for edited source ${url}:`, error);
      });

    res.redirect('/sources');
  } catch (error) {
    console.error('Error editing source:', error);
    res.status(500).send('Error editing source');
  }
}

const deleteSource = async (req, res) => {
  try {
    const { id } = req.params;

    await connection;
    const db = client.db(dbName);
    const collection = db.collection('urls');

    await collection.deleteOne({ _id: require('mongodb').ObjectId(id) });

    console.log(`Deleted source: ${id}`);
    res.redirect('/sources');
  } catch (error) {
    console.error('Error deleting source:', error);
    res.status(500).send('Error deleting source');
  }
}

const refreshSource = async (req, res) => {
  try {
    const { id } = req.params;

    await connection;
    const db = client.db(dbName);
    const collection = db.collection('urls');

    // Get the source by ID
    const source = await collection.findOne({ _id: require('mongodb').ObjectId(id) });

    if (!source) {
      return res.status(404).json({ success: false, error: 'Source not found' });
    }

    console.log(`🔄 Manual refresh triggered for source: ${source.name} (${source.url})`);

    // Start immediate scan and return results
    try {
      const result = await scanSingleSource(source.url);

      // Update last refreshed timestamp
      await collection.updateOne(
        { _id: require('mongodb').ObjectId(id) },
        { $set: { lastRefreshed: new Date() } }
      );

      console.log(`✅ Manual refresh completed for ${source.name}: ${result.scanned}/${result.total} articles processed`);

      res.json({
        success: true,
        result: {
          scanned: result.scanned,
          total: result.total,
          failed: result.failed || (result.total - result.scanned),
          source: source.name,
          url: source.url
        }
      });
    } catch (scanError) {
      console.error(`❌ Manual refresh failed for ${source.name}:`, scanError.message);
      res.status(500).json({
        success: false,
        error: `Scan failed: ${scanError.message}`,
        source: source.name
      });
    }
  } catch (error) {
    console.error('Error refreshing source:', error);
    res.status(500).json({ success: false, error: 'Error refreshing source' });
  }
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
      res.render('pages/graph', {
        results: { days: duration, data: Object.values(idList) },
        dateList: dateList,
        dates: dates,
        title: 'Daily News Readability Report',
        buildTimestamp: BUILD_TIMESTAMP,
        buildVersion: BUILD_VERSION
      })
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
      res.render('pages/daily', {
        results,
        dates: dates,
        title: 'Daily News Readability Report',
        buildTimestamp: BUILD_TIMESTAMP,
        buildVersion: BUILD_VERSION
      })
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

// Source management routes
app.route('/sources').get(getSources);
app.route('/sources/add').post(addSource);
app.route('/sources/edit/:id').post(editSource);
app.route('/sources/delete/:id').post(deleteSource);
app.route('/sources/refresh/:id').post(refreshSource);

app.route('/source/:origin').get(getOrigin);
app.route('/daily').get(getDaily);
app.route('/graph').get(getGraph);
app.route('/export').get(exportToCSV)
app.route('/add-url').get(addUrl);
app.route('/scan').get(scanUrl);
app.route('/').get((req, res) => res.redirect('/sources'));


startCron()