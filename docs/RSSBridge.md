# RSS-Bridge Component Documentation

## Overview
RSS-Bridge is a PHP-based service that creates RSS feeds for websites that don't provide them natively. This component runs as a Docker container and provides custom bridges for major news organizations.

## Purpose
Many news websites don't offer RSS feeds, making it difficult to programmatically monitor their content. RSS-Bridge solves this by:
- Scraping website content using custom bridge scripts
- Converting scraped content into standardized RSS format
- Providing consistent RSS endpoints for the main application to consume

## Container Configuration
- **Image**: `rssbridge/rss-bridge:latest`
- **Port**: `30002:80` (accessible at `localhost:30002`)
- **Network**: `readable` (internal Docker network)

## File Structure
```
rss-bridge/
├── bridges/                    # Custom bridge implementations
│   ├── APNewsPoliticsBridge.php   # Associated Press Politics
│   ├── APNewsTopNewsBridge.php    # Associated Press Top News  
│   └── ReutersBridge.php          # Reuters news
└── whitelist.txt              # Allowed bridges configuration
```

## Custom Bridges

### 1. **APNewsPoliticsBridge.php**
- **Target**: Associated Press Politics section
- **URI**: `https://apnews.com/hub/politics`
- **Functionality**:
  - Scrapes AP Politics hub page
  - Extracts article cards using CSS selectors (`.FeedCard`)
  - Collects headlines, timestamps, authors, and full article content
  - Limits to 15 most recent articles
  - Caches content for 5 minutes (300 seconds)

### 2. **APNewsTopNewsBridge.php**
- **Target**: Associated Press Top News
- **URI**: `https://apnews.com/`
- **Functionality**: Similar to politics bridge but for main news feed

### 3. **ReutersBridge.php**
- **Target**: Reuters news
- **Functionality**: Extracts Reuters articles with similar pattern

## Bridge Architecture

### Common Bridge Pattern
```php
class APNewsPoliticsBridge extends BridgeAbstract {
    const NAME = 'AP: Politics';
    const URI = 'https://apnews.com/hub/politics';
    const DESCRIPTION = 'Associated Press: Politics Section';
    const CACHE_TIMEOUT = 3600;
    const MAINTAINER = 'Pixelmixer';

    public function collectData() {
        // 1. Fetch HTML content with caching
        $html = getSimpleHTMLDOMCached($this->getURI(), 300);
        
        // 2. Find article elements using CSS selectors
        $stories = $html->find('.FeedCard');
        
        // 3. Extract data from each article
        foreach ($stories as $element) {
            $item['uri'] = // Extract article URL
            $item['title'] = // Extract headline
            $item['timestamp'] = // Extract publication date
            $item['author'] = // Extract author information
            $item['content'] = // Extract full article content
            
            $this->items[] = $item;
        }
    }
}
```

## Configuration Files

### whitelist.txt
```
*
```
- Contains `*` to allow all bridges
- Can be configured to restrict which bridges are available
- Security measure to control bridge access

## Data Extraction Process

### 1. **Content Discovery**
- Uses CSS selectors to find article containers
- Typically targets common news site patterns (`.FeedCard`, `.Article`)

### 2. **Metadata Extraction**
- **Headlines**: Usually from `h1` or headline-specific classes
- **Timestamps**: From `data-source` attributes or time elements
- **Authors**: From byline sections, cleaned and formatted

### 3. **Content Retrieval**
- Makes secondary requests to individual article URLs
- Extracts main article content from dedicated containers
- Caches content to reduce server load

## Caching Strategy
- **Page-level caching**: 300 seconds (5 minutes) for article lists
- **Article-level caching**: Individual articles cached separately
- **Global timeout**: 3600 seconds (1 hour) default
- **Purpose**: Reduces load on target websites and improves performance

## RSS Output Format
Generated RSS feeds include:
- **Standard RSS 2.0 format**
- **Item elements**:
  - `<title>`: Article headline
  - `<link>`: Original article URL
  - `<description>`: Full article content (HTML)
  - `<pubDate>`: Publication timestamp
  - `<author>`: Article author(s)

## Integration with Main Application
1. **RSS-Bridge generates feeds** at `localhost:30002/bridge-name`
2. **Main application** adds these URLs to MongoDB `urls` collection
3. **Scheduled crawler** treats bridge-generated feeds like native RSS feeds
4. **Content processing** follows same pipeline as native RSS feeds

## Key Features
- **Standardized output**: All bridges produce consistent RSS format
- **Intelligent caching**: Reduces load on source websites
- **Modular design**: Easy to add new bridges for additional news sources
- **Error handling**: Graceful fallbacks for failed requests
- **Content preservation**: Maintains original article formatting

## Supported News Sources
- **Associated Press**: Politics and general news
- **Reuters**: International news coverage
- **Extensible**: Framework supports adding additional news sources

## Access URLs
- Bridge Interface: `http://localhost:30002`
- AP Politics Feed: `http://localhost:30002/?action=display&bridge=APNewsPolitics&format=Atom`
- AP Top News Feed: `http://localhost:30002/?action=display&bridge=APNewsTopNews&format=Atom`
- Reuters Feed: `http://localhost:30002/?action=display&bridge=Reuters&format=Atom`
