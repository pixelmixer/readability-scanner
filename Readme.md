Readability Scanner
------

This project simply runs a small node script along with a premade [readability-js docker server](https://hub.docker.com/r/phpdockerio/readability-js-server). The intent is to make it easier for scripts which need to parse the main content of web pages (including news, blogs, products, etc...). The readability-js server handles fetching and removing content secondary content, like navigation, sidebars, and ads, from the article content.

### Getting Started
Prerequisites
- Docker

Steps:
1) Run `docker-compose up`.
2) Open http://localhost:49160/?url=https://apnews.com/
3) Replace https://apnews.com with the intended target website, it works best on individual articles.
4) Consider consuming the response from #2 in a GET request as part of a more complex application.