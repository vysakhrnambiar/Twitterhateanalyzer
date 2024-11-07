Twitter Analytics Dashboard
This project is a Twitter Analytics Dashboard designed to help users understand and manage their Twitter experience by analyzing tweet sentiment, visualizing trends, identifying popular topics, and discovering new accounts outside their typical network. By using Playwright for automated tweet extraction and the OpenAI API for sentiment analysis, this tool is accessible to users who don’t want to use a Twitter API key but want a broader perspective on their feed.

Purpose
This tool is ideal for personal use, especially for those who feel that Twitter has become overly negative or who are stuck in an echo chamber. It provides insights into the sentiment of tweets and highlights new trends, giving users a way to discover fresh perspectives and reduce exposure to harmful or repetitive content.

Features
Sentiment Analysis: Analyze sentiment distribution and timeline for tweets, categorized by positive, neutral, and negative sentiments using the OpenAI API.
Category Analysis: View trends and counts of tweets categorized by custom-defined tags.
Trending Topics: Display top trending topics based on tweet counts.
Recommended Accounts: Word cloud visualization for suggested Twitter accounts to follow.
Tweets Filter and View: Filter tweets by sentiment or category and view details.
Project Structure
dashboard.py: Main backend component handling data fetching and preprocessing.
Gettweets.py: Module using Playwright to automate Twitter data extraction without needing a Twitter API key.
screenshots_analyze.py: Module for analyzing images (such as screenshots) to retrieve tweet information.
start.py: Main entry point to initialize and run the application.
tweet_analyzer.py: Uses the OpenAI API to analyze tweet text for sentiment and categorization.
dashboard.html: Frontend for displaying analytics data and visualizations.
setup.bat: Batch file to automate setup on Windows systems.
Setup and Installation
Clone the repository:

bash
Copy code
git clone https://github.com/yourusername/Twitter-Analytics-Dashboard.git
cd Twitter-Analytics-Dashboard
Install Dependencies:

Windows: Run setup.bat, which installs the necessary Python libraries and dependencies.
Other OS: Install the required packages manually, such as playwright, openai, flask, and any other specified in the project.
Additionally, ensure you have your OpenAI API key for tweet analysis.

Run the Application: Execute the start script:

bash
Copy code
python start.py
Access the Dashboard: Open your web browser and navigate to http://localhost:2001 to view the dashboard.

Usage
Select Date Range: Use the date range picker to select the desired period for analytics.
View Sentiment and Category Trends: Sentiment and category sections provide detailed analysis with distribution lists and charts.
Check Trending Topics: Displays topics based on tweet mentions.
Filter Tweets: Filter tweets based on sentiment or category for a more refined view.
Word Cloud: Check the word cloud for recommended accounts to help broaden your Twitter network.
Technologies Used
Backend: Python, Flask
Frontend: HTML, Tailwind CSS, Chart.js, D3.js
Data Extraction: Playwright for automated Twitter data extraction
Analysis: OpenAI API for sentiment and category analysis
