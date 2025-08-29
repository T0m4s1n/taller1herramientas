BOT_NAME = 'motherless_homes_project'
SPIDER_MODULES = ['motherless_spider']
NEWSPIDER_MODULE = 'motherless_spider'

ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
COOKIES_ENABLED = False

DEFAULT_REQUEST_HEADERS = {
   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
   'Accept-Language': 'en',
   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
