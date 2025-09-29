<?php
	// PHP code here
    class APNewsTopNewsBridge extends BridgeAbstract {
        const NAME = 'AP: Top News';
        const URI = 'https://apnews.com/hub/ap-top-news';
        const DESCRIPTION = 'Associated Press: Top News Section';
        const CACHE_TIMEOUT = 3600;
        const MAINTAINER = 'Pixelmixer';

        public function collectData()
        {
            $html = getSimpleHTMLDOMCached($this->getURI(), 300);
            $stories = $html->find('.FeedCard');
            $i = 0;

            foreach ($stories as $element) {
                if($i == 15) {
                    break;
                }
                $item['uri'] = $this->getURI() . '/../../..' . $element->find('a', 0)->href;

                $headline = $element->find('.CardHeadline', 0);
                $item['title'] = $headline->find('h1', 0)->plaintext;
                $item['timestamp'] = $headline->find('.Timestamp', 0)->attr['data-source'];
                $item['author'] = join(", ", explode(" and ", str_replace("By ", "", $headline->find('span[class^=Component-bylines]', 0)->plaintext)));

                // // Get the article content
                $articleHtml = getSimpleHTMLDOMCached($item['uri'], 300);
                $articleContents = $articleHtml->find('.Article', 0)->innertext;

                $item['content'] = $articleContents;
                $this->items[] = $item;
                $i++;
            }
        }
    }

