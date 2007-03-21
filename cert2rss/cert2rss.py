#!/usr/bin/python2.3

import BeautifulSoup
import PyRSS2Gen 
import feedparser
import urllib
import feedparser
import re
import time, datetime

MASTER_FEED = 'http://www.us-cert.gov/channels/bulletins.rdf'
XML_OUT = '/var/web/freshfoo/docs/cert.xml'

#XXX: error handling (report in feed)
#       - what if feed can't be parsed at all (get pickle of last and add error)

rDATE = re.compile('through (\w+ \d+, \d\d\d\d)')
rMULTISPACE = re.compile('\s\s+')

class CertFeed:

    def __init__(self):
        self.rss = PyRSS2Gen.RSS2(
                'US-CERT Cyber Security Bulletins (split)',
                'http://www.us-cert.gov/cas/bulletins/',
                'This feed provides individual items from the US-CERT ' \
                    'Bullentin summaries. Only UNIX and Multi-OS items are ' \
                    'included',
                pubDate=datetime.datetime.utcnow(),
            )
  
    def add_rssitem(self, item):
        self.rss.items.append(item)

    def add_bulletin(self, url):

        # Read and parse the page
        page = urllib.urlopen(url)
        soup = BeautifulSoup.BeautifulSoup(page.read())
        page.close()

        # Pull out the date string from the title
        m = rDATE.search(soup.first('title').string)
        pagetime = time.mktime(time.strptime(m.group(1), "%B %d, %Y"))
        pagetime = datetime.datetime.fromtimestamp(pagetime)

        for section in (
                'UNIX / Linux Operating Systems',
                'Multiple Operating Systems',
                ):
            for title, desc, link in self._parse_entries(soup, url, section):
                self.add_rssitem(PyRSS2Gen.RSSItem(
                        title=title,
                        description=desc,
                        link=link,
                        guid=link,
                        pubDate=pagetime,
                    ))
 
    def _parse_entries(self, soup, url, section_heading):

        # Find section
        headertext = soup.firstText(section_heading)
        titlelist = headertext.findNext('ul')

        items = []
        for item in titlelist('li'):
            # Pull out links and titles
            anchor = item.findNext('a')
            link = url + anchor['href']

            title = None
            desc = None
            if len(anchor) == 0:
                title = anchor.string
            else:
                for anchoritem in anchor:
                    if anchoritem.string is not BeautifulSoup.Null:
                        title = anchoritem.string
                        break

            if title:
                # Grab the description by finding where the href goes
                detail_anchor = soup.first('a', {'name': anchor['href'][1:] })
                desc_holder = detail_anchor.findNext('td')
                if len(desc_holder) > 0:
                    desc_holder = desc_holder.contents[0]
                desc = desc_holder.string[:800]

            if title and desc:
                title = clean_whitespace(title)
                desc = clean_whitespace(desc)

                # Report the entry
                yield (title, desc, link)

    def publish(self, outfile):
        self.rss.write_xml(outfile)

def clean_whitespace(s):

    # Remove newlines and collapse whitespace
    s = s.replace('\n', ' ')
    s = s.replace('\r', ' ')
    s = rMULTISPACE.sub(' ', s)
    return s

def parse_cert(sourcefeed, xmloutpath):
    
    src = feedparser.parse(sourcefeed)    

    outfeed = CertFeed()

    for entry in src.entries:
        print clean_whitespace(entry.title)
        outfeed.add_bulletin(entry.link)
        
    outfeed.publish(open(xmloutpath, 'w'))

if __name__ == '__main__':
    parse_cert(MASTER_FEED, XML_OUT)
