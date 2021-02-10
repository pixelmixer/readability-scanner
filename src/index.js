'use strict';

const express = require('express');
const fetch = require('node-fetch');
const stripHtml = require("string-strip-html");



// Constants
const PORT = 8080;
const HOST = '0.0.0.0';

// App
const app = express();
app.get('/', (req, res) => {
    console.log(req.query.url)

    if(!req.query.url){
        res.status(404).send('Please include a url to search: like: ?url=http://ap.com/article-name')
    }

    const body = { url: req.query.url };

    fetch('http://readability:3000', {
        method: 'post',
        body:    JSON.stringify(body),
        headers: { 'Content-Type': 'application/json' },
    })
    .then(res => res.json())
    .then(json => {
        console.log(json.content, json)
        if(json.content){
            res.send(json.content)
        } else {
            res.send('No content found in the page response')
        }
    })
    .catch(err => res.status(500).send(err));


    // const data = JSON.stringify({
    //     url: req.query.url
    // })


    // const options = {
    //     hostname: '192.168.86.41',
    //     port: 3000,
    //     method: 'POST',
    //     headers: {
    //         'Content-Type': 'application/json',
    //         'Content-Length': data.length
    //     }
    // }

    // const request = https.request(options, res => {
    //     console.log(`statusCode: ${res.statusCode}`)

    //     res.on('data', d => {
    //         res.send(`Hello World, ${request.query.url}`);
    //     })
    // })
});

app.listen(PORT, HOST);
console.log(`Running on http://${HOST}:${PORT}`);