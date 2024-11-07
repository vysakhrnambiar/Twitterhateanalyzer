import sqlite3
import json
import os
import logging
import pytz
from datetime import datetime
import aiohttp
import asyncio

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tweet_analyzer.log')
    ]
)

class TweetAnalyzer:
    def __init__(self):
        self.DB_FILE = "twitter_data.db"
        self.API_KEY_FILE = "openai_key.txt"
        self.BATCH_SIZE = 25
        self.api_key = self.get_api_key()
        self.init_database()

    def get_api_key(self):
        """Get OpenAI API key from file or user input"""
        if os.path.exists(self.API_KEY_FILE):
            try:
                with open(self.API_KEY_FILE, 'r') as f:
                    key = f.read().strip()
                if key:
                    logging.info("API key loaded from file")
                    return key
            except Exception as e:
                logging.error(f"Error reading API key file: {e}")
        
        print("\nOpenAI API key not found or invalid.")
        key = input("Please enter your OpenAI API key: ").strip()
        
        try:
            with open(self.API_KEY_FILE, 'w') as f:
                f.write(key)
            logging.info("API key saved to file")
        except Exception as e:
            logging.error(f"Error saving API key: {e}")
        
        return key

    def init_database(self):
        """Initialize database with new fields if they don't exist"""
        conn = sqlite3.connect(self.DB_FILE)
        cursor = conn.cursor()

        # Get existing columns in tweets table
        cursor.execute("PRAGMA table_info(tweets)")
        existing_columns = {col[1] for col in cursor.fetchall()}

        # Add new columns if they don't exist
        new_columns = {
            'processed': 'BOOLEAN DEFAULT FALSE',
            'processed_at': 'DATETIME',
            'summary': 'TEXT',
            'sentiment': 'TEXT',
            'category': 'TEXT'
        }

        for column, data_type in new_columns.items():
            if column not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE tweets ADD COLUMN {column} {data_type}")
                    logging.info(f"Added new column: {column}")
                except sqlite3.OperationalError as e:
                    logging.warning(f"Column {column} already exists or error: {e}")

        conn.commit()
        conn.close()
        logging.info("Database initialization completed")

    def get_unprocessed_tweets(self):
        """Get batch of unprocessed tweets"""
        conn = sqlite3.connect(self.DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT tweet_id, text, author, timestamp
            FROM tweets
            WHERE processed IS FALSE OR processed IS NULL
            LIMIT ?
        ''', (self.BATCH_SIZE,))
        
        tweets = cursor.fetchall()
        conn.close()
        
        return [(tweet[0], {
            'id': tweet[0],
            'text': tweet[1],
            'author': tweet[2],
            'timestamp': tweet[3]
        }) for tweet in tweets]

    async def analyze_tweets(self, tweets):
        """Analyze batch of tweets using GPT-4"""
        tweets_data = []
        for _, tweet in tweets:
            tweets_data.append({
                "id": tweet['id'],
                "text": tweet['text'],
                "author": tweet['author'],
                "timestamp": tweet['timestamp']
            })
        
        prompt = f"""
        Analyze these {len(tweets)} tweets and return a JSON object with an "analyses" array containing analysis for each tweet.

        For each tweet provide:
        1. A brief summary (max 50 words)
        2. The emotional tone/sentiment (one of: hateful, angry, happy, neutral, innovative, excited, sad, concerned, teaching)
        3. A category describing the tweet's nature (e.g., news, opinion, announcement, discussion)

        Expected JSON format:
        {{
            "analyses": [
                {{
                    "id": "tweet_id",
                    "summary": "brief summary",
                    "sentiment": "emotional_tone",
                    "category": "tweet_category"
                }},
                ...
            ]
        }}

        Tweets to analyze: {json.dumps(tweets_data, indent=2)}
        """

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a tweet analysis system. Return only valid JSON matching the specified format exactly."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": 2000,
                        "response_format": { "type": "json_object" }
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Log the raw response for debugging
                        logging.info(f"Raw GPT response: {content}")
                        
                        # Parse and validate the response
                        try:
                            parsed_content = json.loads(content)
                            if 'analyses' not in parsed_content:
                                logging.error("Response missing 'analyses' array")
                                return None
                            return parsed_content
                        except json.JSONDecodeError as e:
                            logging.error(f"Failed to parse GPT response as JSON: {e}")
                            return None
                    else:
                        error_text = await response.text()
                        logging.error(f"OpenAI API error: {error_text}")
                        return None
        except Exception as e:
            logging.error(f"Error analyzing tweets: {e}")
            return None

    def save_analysis(self, analysis_results):
        """Save analysis results to database"""
        if not analysis_results or 'analyses' not in analysis_results:
            logging.error("Invalid analysis results format")
            return

        conn = sqlite3.connect(self.DB_FILE)
        cursor = conn.cursor()
        current_time = datetime.now(pytz.UTC).isoformat()

        try:
            for result in analysis_results['analyses']:
                logging.info(f"Processing result for tweet {result.get('id', 'unknown')}")
                
                if not all(key in result for key in ['id', 'summary', 'sentiment', 'category']):
                    logging.warning(f"Skipping incomplete result: {result}")
                    continue

                cursor.execute('''
                    UPDATE tweets
                    SET processed = TRUE,
                        processed_at = ?,
                        summary = ?,
                        sentiment = ?,
                        category = ?
                    WHERE tweet_id = ?
                ''', (
                    current_time,
                    result['summary'],
                    result['sentiment'],
                    result['category'],
                    result['id']
                ))
            
            conn.commit()
            logging.info(f"Successfully saved analysis for {len(analysis_results['analyses'])} tweets")
            
        except Exception as e:
            logging.error(f"Error saving analysis results: {e}")
            conn.rollback()
        finally:
            conn.close()

    async def process_tweets(self):
        """Main processing function"""
        total_processed = 0
        
        while True:
            # Get batch of unprocessed tweets
            tweets = self.get_unprocessed_tweets()
            if not tweets:
                logging.info("No more tweets to process")
                break
                
            batch_size = len(tweets)
            logging.info(f"Processing batch of {batch_size} tweets")
            
            # Analyze tweets
            analysis_results = await self.analyze_tweets(tweets)
            if analysis_results:
                # Save results
                self.save_analysis(analysis_results)
                total_processed += batch_size
                logging.info(f"Completed processing batch. Total tweets processed: {total_processed}")
            else:
                logging.error("Failed to analyze batch, skipping...")
            
            # Small delay between batches
            await asyncio.sleep(1)
        
        logging.info(f"Processing completed. Total tweets analyzed: {total_processed}")

async def main():
    analyzer = TweetAnalyzer()
    await analyzer.process_tweets()

if __name__ == "__main__":
    asyncio.run(main())