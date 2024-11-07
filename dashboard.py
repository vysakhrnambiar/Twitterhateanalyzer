from flask import Flask, render_template, jsonify, request
import sqlite3
from datetime import datetime, timedelta
import json
import pytz

app = Flask(__name__)

def get_db_connection():
    """Create a connection to Twitter database"""
    conn = sqlite3.connect('twitter_data.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/sentiment_counts')
def sentiment_counts():
    """Get counts of tweets by sentiment"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT sentiment, COUNT(*) as count
        FROM tweets
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
        ORDER BY count DESC
    ''')
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(results)

@app.route('/api/category_counts')
def category_counts():
    """Get counts of tweets by category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT category, COUNT(*) as count
        FROM tweets
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY count DESC
    ''')
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(results)

@app.route('/api/sentiment_timeline')
def sentiment_timeline():
    """Get sentiment counts over time"""
    start_date = request.args.get('start_date', default=None)
    end_date = request.args.get('end_date', default=None)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            DATE(timestamp) as date,
            sentiment,
            COUNT(*) as count
        FROM tweets
        WHERE sentiment IS NOT NULL
    '''
    
    params = []
    if start_date:
        query += ' AND DATE(timestamp) >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND DATE(timestamp) <= ?'
        params.append(end_date)
    
    query += ' GROUP BY DATE(timestamp), sentiment ORDER BY date'
    
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(results)

@app.route('/api/category_timeline')
def category_timeline():
    """Get category counts over time"""
    start_date = request.args.get('start_date', default=None)
    end_date = request.args.get('end_date', default=None)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            DATE(timestamp) as date,
            category,
            COUNT(*) as count
        FROM tweets
        WHERE category IS NOT NULL
    '''
    
    params = []
    if start_date:
        query += ' AND DATE(timestamp) >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND DATE(timestamp) <= ?'
        params.append(end_date)
    
    query += ' GROUP BY DATE(timestamp), category ORDER BY date'
    
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(results)

@app.route('/api/tweets')
def get_tweets():
    """Get tweets with optional filtering"""
    sentiment = request.args.get('sentiment', default=None)
    category = request.args.get('category', default=None)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            tweet_id,
            author,
            text,
            timestamp,
            sentiment,
            category,
            summary
        FROM tweets
        WHERE 1=1
    '''
    
    params = []
    if sentiment and sentiment != 'all':
        query += ' AND sentiment = ?'
        params.append(sentiment)
    if category and category != 'all':
        query += ' AND category = ?'
        params.append(category)
    
    query += ' ORDER BY timestamp DESC LIMIT 100'
    
    cursor.execute(query, params)
    tweets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(tweets)

@app.route('/api/filters')
def get_filters():
    """Get unique sentiments and categories for filters"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get unique sentiments
    cursor.execute('SELECT DISTINCT sentiment FROM tweets WHERE sentiment IS NOT NULL')
    sentiments = [row[0] for row in cursor.fetchall()]
    
    # Get unique categories
    cursor.execute('SELECT DISTINCT category FROM tweets WHERE category IS NOT NULL')
    categories = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify({
        'sentiments': sentiments,
        'categories': categories
    })

# Add these new routes to your existing app.py
@app.route('/api/trends')
def get_trends():
    """Get trending topics with counts"""
    start_date = request.args.get('start_date', default=None)
    end_date = request.args.get('end_date', default=None)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            topic,
            category,
            COUNT(*) as count
        FROM trending_topics
        WHERE 1=1
    '''
    
    params = []
    if start_date:
        query += ' AND DATE(timestamp) >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND DATE(timestamp) <= ?'
        params.append(end_date)
    
    query += ' GROUP BY topic, category ORDER BY count DESC LIMIT 10'
    
    cursor.execute(query, params)
    trends = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(trends)

@app.route('/api/recommendations')
def get_recommendations():
    """Get account recommendations with frequency"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            username,
            display_name,
            COUNT(*) as frequency
        FROM follow_recommendations
        WHERE timestamp >= datetime('now', '-7 days')
        GROUP BY username, display_name
        ORDER BY frequency DESC
        LIMIT 20
    ''')
    
    recommendations = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(recommendations)

if __name__ == '__main__':
    app.run(debug=True, port=2001)