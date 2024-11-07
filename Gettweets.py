import sqlite3
import json
import os
from playwright.sync_api import sync_playwright
from datetime import datetime
import logging
import pytz
import sys

if sys.platform.startswith('win'):
    # For Windows
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Set up logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Console handler with stdout
        logging.FileHandler('tweet_extractor.log', encoding='utf-8')  # File handler with UTF-8
    ]
)

class TweetExtractor:
    def __init__(self):
        self.COOKIES_FILE = "cookies.json"
        self.DB_FILE = "twitter_data.db"
        self.SCREENSHOTS_DIR = "screenshots"
        
        # Ensure screenshots directory exists
        if not os.path.exists(self.SCREENSHOTS_DIR):
            os.makedirs(self.SCREENSHOTS_DIR)
            logging.info(f"Created screenshots directory: {self.SCREENSHOTS_DIR}")
        
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with required tables"""
        logging.info("Initializing database...")
        conn = sqlite3.connect(self.DB_FILE)
        c = conn.cursor()
        
        # Tweets table
        c.execute('''
            CREATE TABLE IF NOT EXISTS tweets (
                tweet_id TEXT PRIMARY KEY,
                author TEXT,
                author_handle TEXT,
                timestamp DATETIME,
                text TEXT,
                url TEXT,
                media_links TEXT,
                quoted_tweet_link TEXT,
                is_original BOOLEAN
            )
        ''')
        
        # Metrics table
        c.execute('''
            CREATE TABLE IF NOT EXISTS tweet_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id TEXT,
                timestamp DATETIME,
                replies INTEGER,
                reposts INTEGER,
                likes INTEGER,
                views INTEGER,
                bookmarks INTEGER,
                FOREIGN KEY (tweet_id) REFERENCES tweets (tweet_id)
            )
        ''')
        
        # Links table
        c.execute('''
            CREATE TABLE IF NOT EXISTS tweet_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tweet_id TEXT,
                link TEXT,
                first_seen DATETIME,
                processed BOOLEAN DEFAULT FALSE,
                processed_at DATETIME,
                FOREIGN KEY (tweet_id) REFERENCES tweets (tweet_id),
                UNIQUE(tweet_id, link)
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.info("Database initialized successfully")

    def save_cookies(self, context):
        """Save browser cookies to file"""
        logging.info("Saving session cookies...")
        cookies = context.cookies()
        with open(self.COOKIES_FILE, "w") as f:
            json.dump(cookies, f)
        logging.info("Cookies saved successfully")

    def load_cookies(self, context):
        """Load cookies from file if they exist"""
        if os.path.exists(self.COOKIES_FILE):
            logging.info("Loading session cookies...")
            with open(self.COOKIES_FILE, "r") as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
            return True
        logging.info("No cookies file found")
        return False

    def check_login(self, page):
        """Check if user is logged in"""
        logging.info("Checking login status...")
        try:
            # Wait for home timeline or profile icon
            page.wait_for_selector('a[aria-label="Profile"]', timeout=5000)
            logging.info("User is logged in")
            return True
        except:
            logging.info("User is not logged in")
            return False

    def extract_tweets_and_metrics(self, page):
        """Extract tweets, metrics, and external links using precise HTML structure"""

        logging.info("Trying for more tweets")
        return page.evaluate('''
        () => {
            const tweets = [];
            const articleElements = document.querySelectorAll('article[data-testid="tweet"]');
            
            for (const article of articleElements) {
                // Check for repost indicators
                const socialContext = article.querySelector('div[role="group"] svg[data-testid="socialContext"]');
                const repostText = article.querySelector('span[data-testid="socialContext"]');
                const isRepost = socialContext || (repostText && repostText.textContent.includes('reposted'));
                
                if (1) {
                    const tweetTextElement = article.querySelector('div[data-testid="tweetText"]');
                    const authorElement = article.querySelector('div[data-testid="User-Name"] div:first-child span');
                    const authorHandleElement = article.querySelector('div[data-testid="User-Name"] div[dir="ltr"]');
                    const timestampElement = article.querySelector('time');
                    const tweetLinkElement = article.querySelector('a[href*="/status/"]');

                    // Improved metric extraction function
                    const getMetricValue = (testId, isLink = false) => {
                        // Special handling for views which have a different structure
                        if (isLink) {
                            const viewsElement = article.querySelector('a[href*="/analytics"] span[data-testid="app-text-transition-container"] span span.css-1jxf684.r-bcqeeo');
                            console.log(`Views element found:`, viewsElement?.textContent);
                            if (!viewsElement) return 0;
                            const text = viewsElement.textContent.trim();
                            if (text.includes('K')) {
                                return parseFloat(text.replace('K', '')) * 1000;
                            } else if (text.includes('M')) {
                                return parseFloat(text.replace('M', '')) * 1000000;
                            }
                            return parseInt(text || '0', 10);
                        }

                        // Regular metrics (replies, reposts, likes, bookmarks)
                        const container = article.querySelector(`[data-testid="${testId}"]`);
                        console.log(`Container for ${testId}:`, container?.outerHTML);
                        if (!container) return 0;

                        const innerSpan = container.querySelector('span[data-testid="app-text-transition-container"] span span');
                        console.log(`Value for ${testId}:`, innerSpan?.textContent);
                        if (!innerSpan) return 0;
                        
                        const text = innerSpan.textContent.trim();
                        if (text.includes('K')) {
                            return parseFloat(text.replace('K', '')) * 1000;
                        } else if (text.includes('M')) {
                            return parseFloat(text.replace('M', '')) * 1000000;
                        }
                        return parseInt(text || '0', 10);
                    };

                    // Extract all metrics
                    const metrics = {
                        replies: getMetricValue('reply'),
                        reposts: getMetricValue('retweet'),
                        likes: getMetricValue('like'),
                        views: getMetricValue('analytics', true),
                        bookmarks: getMetricValue('bookmark')
                    };

                    // Debug log the metrics
                    console.log('Extracted metrics:', JSON.stringify(metrics));
                    
                    // Extract media links
                    const mediaElements = article.querySelectorAll('a[href*="/photo/"], a[href*="/video/"]');
                    const mediaLinks = Array.from(mediaElements).map(media => {
                        const href = media.getAttribute('href');
                        return href ? 'https://twitter.com' + href : null;
                    }).filter(Boolean);
                    
                    // Extract external links (excluding twitter.com)
                    const allLinks = Array.from(article.querySelectorAll('a[href]'))
                        .map(a => a.getAttribute('href'))
                        .filter(href => href && 
                               !href.includes('twitter.com') && 
                               !href.includes('x.com') && 
                               href.startsWith('http'));
                    
                    if (tweetTextElement && authorElement && timestampElement && tweetLinkElement) {
                        const tweetUrl = 'https://twitter.com' + tweetLinkElement.getAttribute('href');
                        
                        tweets.push({
                            author: authorElement.textContent,
                            author_handle: authorHandleElement?.textContent?.trim(),
                            timestamp: timestampElement.getAttribute('datetime'),
                            text: tweetTextElement.textContent,
                            url: tweetUrl,
                            media_links: mediaLinks.length > 0 ? JSON.stringify(mediaLinks) : null,
                            external_links: allLinks.length > 0 ? allLinks : null,
                            metrics: metrics
                        });
                    }
                }
            }
            
            return tweets;
        }
        ''')

    def save_tweets(self, tweets):
        """Save tweets and their metrics to database with detailed logging"""
        conn = sqlite3.connect(self.DB_FILE)
        c = conn.cursor()
        current_time = datetime.now(pytz.UTC).isoformat()
    
        stats = {
            'total_tweets': len(tweets),
            'new_tweets': 0,
            'ignored_tweets': 0,
            'new_metrics': 0,
            'new_links': 0,
            'ignored_links': 0
        }
        
        logging.info(f"\n=== Processing {stats['total_tweets']} tweets ===")
        
        for tweet in tweets:
            tweet_id = tweet['url'].split("/status/")[-1]
            
            # First check if tweet exists
            c.execute('SELECT tweet_id FROM tweets WHERE tweet_id = ?', (tweet_id,))
            tweet_exists = c.fetchone() is not None
            
            try:
                # Save tweet
                c.execute('''
                    INSERT OR IGNORE INTO tweets (
                        tweet_id, author, author_handle, timestamp, text, 
                        url, media_links, is_original
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tweet_id,
                    tweet['author'],
                    tweet['author_handle'],
                    tweet['timestamp'],
                    tweet['text'],
                    tweet['url'],
                    tweet['media_links'],
                    True
                ))
                
                if c.rowcount > 0:
                    stats['new_tweets'] += 1
                    logging.info(f"New tweet saved: {tweet_id} by {tweet['author']}")
                else:
                    stats['ignored_tweets'] += 1
                    logging.info(f"Tweet ignored (already exists): {tweet_id} by {tweet['author']}")
                
                # Always save metrics (they're timestamped)
                c.execute('''
                    INSERT INTO tweet_metrics (
                        tweet_id, timestamp, replies, reposts, likes, 
                        views, bookmarks
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tweet_id,
                    current_time,
                    tweet['metrics']['replies'],
                    tweet['metrics']['reposts'],
                    tweet['metrics']['likes'],
                    tweet['metrics']['views'],
                    tweet['metrics']['bookmarks']
                ))
                stats['new_metrics'] += 1
                
                # Save external links if they exist
                if tweet.get('external_links'):
                    for link in tweet['external_links']:
                        try:
                            c.execute('''
                                INSERT OR IGNORE INTO tweet_links (
                                    tweet_id, link, first_seen
                                ) VALUES (?, ?, ?)
                            ''', (
                                tweet_id,
                                link,
                                current_time
                            ))
                            if c.rowcount > 0:
                                stats['new_links'] += 1
                                logging.debug(f"New link saved: {link} for tweet {tweet_id}")
                            else:
                                stats['ignored_links'] += 1
                                logging.debug(f"Link ignored (already exists): {link} for tweet {tweet_id}")
                                
                        except sqlite3.IntegrityError as e:
                            logging.warning(f"Error saving link: {link} for tweet {tweet_id}: {e}")
                            stats['ignored_links'] += 1
                
            except sqlite3.IntegrityError as e:
                logging.warning(f"Error saving tweet {tweet_id}: {e}")
                stats['ignored_tweets'] += 1
                continue
        
        conn.commit()
        conn.close()
        
        # Print final statistics
        logging.info("\n=== Tweet Processing Summary ===")
        logging.info(f"Total tweets processed: {stats['total_tweets']}")
        logging.info(f"New tweets saved: {stats['new_tweets']}")
        logging.info(f"Tweets ignored (duplicates): {stats['ignored_tweets']}")
        logging.info(f"New metrics records: {stats['new_metrics']}")
        logging.info(f"New links saved: {stats['new_links']}")
        logging.info(f"Links ignored (duplicates): {stats['ignored_links']}")
        logging.info("===============================\n")

    def run(self):
        """Main execution function"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            
            try:
                # First check if we have cookies
                has_cookies = self.load_cookies(context)
                page = context.new_page()
                
                if has_cookies:
                    # Try to use existing cookies
                    logging.info("Attempting to use existing cookies...")
                    page.goto("https://x.com/home")
                    page.wait_for_timeout(10000)  # Wait 10 seconds after navigation
                    
                    if not self.check_login(page):
                        logging.info("Existing cookies invalid, manual login required...")
                        page.goto("https://twitter.com/i/flow/login")
                        page.wait_for_timeout(10000)  # Wait 10 seconds after navigation
                        input("Please log in manually and press Enter when done...")
                        
                        if self.check_login(page):
                            self.save_cookies(context)
                        else:
                            raise Exception("Login failed")
                else:
                    # No cookies, direct to login
                    logging.info("No cookies found, manual login required...")
                    page.goto("https://twitter.com/i/flow/login")
                    page.wait_for_timeout(10000)  # Wait 10 seconds after navigation
                    input("Please log in manually and press Enter when done...")
                    
                    if self.check_login(page):
                        self.save_cookies(context)
                    else:
                        raise Exception("Login failed")

                # Ensure we're on the home timeline
                logging.info("Navigating to home timeline...")
                page.goto("https://x.com/home")
                page.wait_for_timeout(10000)  # Wait 10 seconds after navigation
                page.wait_for_selector('article[data-testid="tweet"]')
                page.wait_for_timeout(10000)  # Wait additional 10 seconds before screenshot
                
                # Take screenshot of first page
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_path = f"{self.SCREENSHOTS_DIR}/timeline_{timestamp}.png"
                page.screenshot(path=screenshot_path, full_page=True, timeout=30000)
                logging.info(f"Screenshot saved: {screenshot_path}")
                
                # Extract tweets
                logging.info(f"Starting tweet extraction. Target: 200 tweets")
                tweets = []
                while len(tweets) < 200:
                    new_tweets = self.extract_tweets_and_metrics(page)
                    tweets.extend(new_tweets)
                    logging.info(f"Current tweet count: {len(tweets)} (Added {len(new_tweets)} new tweets)")
                    
                    if len(tweets) >= 200:
                        tweets = tweets[:200]
                        break
                        
                    # Scroll for more tweets
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    page.wait_for_timeout(10000)  # Wait 10 seconds after each scroll
                
                # Save tweets to database
                logging.info(f"Saving {len(tweets)} tweets to database...")
                self.save_tweets(tweets)
                logging.info("Tweet extraction completed successfully")
                
            except Exception as e:
                logging.error(f"An error occurred: {e}")
            finally:
                browser.close()

if __name__ == "__main__":
    extractor = TweetExtractor()
    extractor.run()