import os
import sqlite3
from datetime import datetime
import logging
import pytz
import base64
import aiohttp
import asyncio
from PIL import Image
import glob
import json
import getpass

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('screenshot_analyzer.log')
    ]
)

class ScreenshotAnalyzer:
    def __init__(self):
        self.DB_FILE = "twitter_data.db"
        self.SCREENSHOTS_DIR = "screenshots"
        self.PROCESSED_DIR = os.path.join(self.SCREENSHOTS_DIR, "processed")
        self.API_KEY_FILE = "openai_key.txt"
        
        # Ensure directories exist
        for directory in [self.SCREENSHOTS_DIR, self.PROCESSED_DIR]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logging.info(f"Created directory: {directory}")
        
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
        """Initialize database with tables for trends and recommendations"""
        conn = sqlite3.connect(self.DB_FILE)
        c = conn.cursor()
        
        # Table for trending topics
        c.execute('''
            CREATE TABLE IF NOT EXISTS trending_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                category TEXT,
                tweet_volume INTEGER,
                timestamp DATETIME,
                screenshot_ref TEXT
            )
        ''')
        
        # Table for who to follow recommendations
        c.execute('''
            CREATE TABLE IF NOT EXISTS follow_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                display_name TEXT,
                description TEXT,
                timestamp DATETIME,
                screenshot_ref TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.info("Database tables initialized successfully")

    def get_latest_screenshot(self):
        """Get the most recent screenshot from the screenshots directory"""
        screenshots = glob.glob(os.path.join(self.SCREENSHOTS_DIR, "timeline_*.png"))
        if not screenshots:
            logging.info("No screenshots found")
            return None
        
        latest_screenshot = max(screenshots, key=os.path.getctime)
        logging.info(f"Found latest screenshot: {latest_screenshot}")
        return latest_screenshot

    def crop_image(self, image_path):
        """Crop the screenshot to 1260x1600 pixels"""
        try:
            with Image.open(image_path) as img:
                cropped = img.crop((0, 0, 1260, 1600))
                
                filename = os.path.basename(image_path)
                processed_path = os.path.join(self.PROCESSED_DIR, f"processed_{filename}")
                
                cropped.save(processed_path)
                logging.info(f"Image cropped and saved: {processed_path}")
                return processed_path
        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return None

    def encode_image(self, image_path):
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def extract_json_from_response(self, content):
        """Extract and validate JSON from LLM response"""
        logging.info("Processing LLM response to extract JSON")
        
        try:
            # First try to parse the entire response as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
            
            # If that fails, try to find JSON within the text
            import re
            json_pattern = r'\{(?:[^{}]|(?R))*\}'
            matches = re.finditer(json_pattern, content)
            
            for match in matches:
                try:
                    json_str = match.group()
                    data = json.loads(json_str)
                    
                    # Validate the structure
                    if not isinstance(data, dict):
                        continue
                    
                    if not all(key in data for key in ['trends', 'recommendations']):
                        continue
                    
                    if not all(isinstance(data[key], list) for key in ['trends', 'recommendations']):
                        continue
                    
                    # Validate trends structure
                    for trend in data['trends']:
                        if not isinstance(trend, dict) or 'topic' not in trend:
                            continue
                    
                    # Validate recommendations structure
                    for rec in data['recommendations']:
                        if not isinstance(rec, dict) or not all(key in rec for key in ['username', 'display_name', 'description']):
                            continue
                    
                    logging.info("Successfully extracted and validated JSON structure")
                    return data
                    
                except json.JSONDecodeError:
                    continue
            
            logging.error("No valid JSON structure found in response")
            return None
            
        except Exception as e:
            logging.error(f"Error extracting JSON: {e}")
            return None

    async def analyze_image(self, image_path):
        """Analyze image using GPT-4 Vision to extract trends and recommendations"""
        image_base64 = self.encode_image(image_path)
        
        prompt = """
        Analyze this Twitter/X screenshot and extract two types of information:
        1. Trending topics from the "Trends for you" section on the right
        2. "Who to follow" recommendations on the right

        Return ONLY the following JSON structure without any additional text or explanation:
        {
            "trends": [
                {
                    "topic": "topic name",
                    "category": "category if shown (e.g., Trending in Tech)",
                    "tweet_volume": number of tweets (null if not shown)
                }
            ],
            "recommendations": [
                {
                    "username": "@handle",
                    "display_name": "Display Name",
                    "description": "brief description shown"
                }
            ]
        }
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
                        "model": "gpt-4o-mini",  # Updated to correct model name
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a JSON-only response bot. You must only return valid JSON without any additional text, markdown, or formatting."
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_base64}"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 1000,
                        "response_format": { "type": "json_object" }
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        try:
                            content = result['choices'][0]['message']['content']
                            # Use the enhanced JSON extraction method
                            data = await self.extract_json_from_response(content)
                            
                            if data:
                                # Clean and normalize the data
                                cleaned_data = {
                                    "trends": [],
                                    "recommendations": []
                                }
                                
                                # Clean trends
                                for trend in data.get('trends', []):
                                    cleaned_trend = {
                                        "topic": str(trend.get('topic', '')).strip(),
                                        "category": str(trend.get('category', '')).strip() or None,
                                        "tweet_volume": int(trend['tweet_volume']) if trend.get('tweet_volume') and str(trend['tweet_volume']).isdigit() else None
                                    }
                                    cleaned_data['trends'].append(cleaned_trend)
                                
                                # Clean recommendations
                                for rec in data.get('recommendations', []):
                                    cleaned_rec = {
                                        "username": str(rec.get('username', '')).strip().strip('@'),
                                        "display_name": str(rec.get('display_name', '')).strip(),
                                        "description": str(rec.get('description', '')).strip()
                                    }
                                    if cleaned_rec['username'] and cleaned_rec['display_name']:
                                        cleaned_data['recommendations'].append(cleaned_rec)
                                
                                return cleaned_data
                            return None
                            
                        except Exception as e:
                            logging.error(f"Error processing GPT response: {e}")
                            return None
                            
                    elif response.status == 401:
                        logging.error("Invalid API key. Please provide a valid key.")
                        if os.path.exists(self.API_KEY_FILE):
                            os.remove(self.API_KEY_FILE)
                        self.api_key = self.get_api_key()
                        return await self.analyze_image(image_path)
                    else:
                        error_text = await response.text()
                        logging.error(f"OpenAI API error: {error_text}")
                        return None
                        
        except Exception as e:
            logging.error(f"Error calling OpenAI API: {e}")
            return None

    def save_to_database(self, data, screenshot_ref, timestamp):
        """Save the extracted data to the database"""
        conn = sqlite3.connect(self.DB_FILE)
        c = conn.cursor()
        
        try:
            # Save trending topics
            for trend in data.get('trends', []):
                c.execute('''
                    INSERT INTO trending_topics 
                    (topic, category, tweet_volume, timestamp, screenshot_ref)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    trend['topic'],
                    trend.get('category'),
                    trend.get('tweet_volume'),
                    timestamp,
                    screenshot_ref
                ))
            
            # Save follow recommendations
            for rec in data.get('recommendations', []):
                c.execute('''
                    INSERT INTO follow_recommendations 
                    (username, display_name, description, timestamp, screenshot_ref)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    rec['username'],
                    rec['display_name'],
                    rec['description'],
                    timestamp,
                    screenshot_ref
                ))
            
            conn.commit()
            logging.info("Data saved to database successfully")
            
        except Exception as e:
            logging.error(f"Database error: {e}")
            conn.rollback()
        finally:
            conn.close()

    def cleanup(self, original_screenshot):
        """Delete the original screenshot file"""
        try:
            os.remove(original_screenshot)
            logging.info(f"Deleted original screenshot: {original_screenshot}")
        except Exception as e:
            logging.error(f"Error deleting original screenshot: {e}")

    async def process(self):
        """Main processing function"""
        try:
            # Get latest screenshot
            original_screenshot = self.get_latest_screenshot()
            if not original_screenshot:
                logging.info("No screenshots to process")
                return
            
            # Extract timestamp from filename
            try:
                # Get just the filename without path
                filename = os.path.basename(original_screenshot)
                # Log the filename for debugging
                logging.info(f"Processing file: {filename}")
                
                # Extract timestamp part more carefully
                # Handle both formats: timeline_YYYYMMDD_HHMMSS.png and timeline_YYYYMMDD.png
                parts = filename.split('_')
                if len(parts) >= 2:
                    timestamp_str = parts[1].split('.')[0]
                    if len(timestamp_str) == 8:  # YYYYMMDD format
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d')
                    else:  # YYYYMMDD_HHMMSS format
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                else:
                    raise ValueError(f"Unexpected filename format: {filename}")
                
                timestamp = pytz.UTC.localize(timestamp)
                logging.info(f"Extracted timestamp: {timestamp}")
            
            except Exception as e:
                logging.error(f"Error parsing timestamp from filename: {e}")
                # Use current time as fallback
                timestamp = datetime.now(pytz.UTC)
                logging.info(f"Using current time instead: {timestamp}")
            
            # Crop image
            processed_image = self.crop_image(original_screenshot)
            if not processed_image:
                return
            
            # Analyze image
            data = await self.analyze_image(processed_image)
            if data:
                # Print the extracted data for verification
                logging.info("Extracted data:")
                print(json.dumps(data, indent=2))
                
                # Save to database
                self.save_to_database(
                    data, 
                    os.path.basename(processed_image),
                    timestamp.isoformat()
                )
                
                # Cleanup original screenshot
                self.cleanup(original_screenshot)
                
            logging.info("Processing completed successfully")
            
        except Exception as e:
            logging.error(f"Error in processing: {e}")

async def main():
    analyzer = ScreenshotAnalyzer()
    await analyzer.process()

if __name__ == "__main__":
    asyncio.run(main())