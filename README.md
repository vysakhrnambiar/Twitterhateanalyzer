<h1>Twitter Analytics Dashboard</h1>

<p>This project is a <strong>Twitter Analytics Dashboard</strong> designed to help users understand and manage their Twitter experience by analyzing tweet sentiment, visualizing trends, identifying popular topics, and discovering new accounts outside their typical network. By using Playwright for automated tweet extraction and the OpenAI API for sentiment analysis, this tool is accessible to users who don’t want to use a Twitter API key but want a broader perspective on their feed.</p>

<h2>Purpose</h2>

<p>This tool is ideal for personal use, especially for those who feel that Twitter has become overly negative or who are stuck in an echo chamber. It provides insights into the sentiment of tweets and highlights new trends, giving users a way to discover fresh perspectives and reduce exposure to harmful or repetitive content.</p>

<h2>Features</h2>

<ul>
  <li><strong>Sentiment Analysis</strong>: Analyze sentiment distribution and timeline for tweets, categorized by positive, neutral, and negative sentiments using the OpenAI API.</li>
  <li><strong>Category Analysis</strong>: View trends and counts of tweets categorized by custom-defined tags.</li>
  <li><strong>Trending Topics</strong>: Display top trending topics based on tweet counts.</li>
  <li><strong>Recommended Accounts</strong>: Word cloud visualization for suggested Twitter accounts to follow.</li>
  <li><strong>Tweets Filter and View</strong>: Filter tweets by sentiment or category and view details.</li>
</ul>

<h2>Project Structure</h2>

<ul>
  <li><code>dashboard.py</code>: Main backend component handling data fetching and preprocessing.</li>
  <li><code>Gettweets.py</code>: Module using Playwright to automate Twitter data extraction without needing a Twitter API key.</li>
  <li><code>screenshots_analyze.py</code>: Module for analyzing images (such as screenshots) to retrieve tweet information.</li>
  <li><code>start.py</code>: Main entry point to initialize and run the application.</li>
  <li><code>tweet_analyzer.py</code>: Uses the OpenAI API to analyze tweet text for sentiment and categorization.</li>
  <li><code>dashboard.html</code>: Frontend for displaying analytics data and visualizations.</li>
  <li><code>setup.bat</code>: Batch file to automate setup on Windows systems.</li>
</ul>

<h2>Setup and Installation</h2>

<ol>
  <li><strong>Clone the repository:</strong>
    <pre><code>git clone https://github.com/vysakhrnambiar/Twitter-Analytics-Dashboard.git
cd Twitter-Analytics-Dashboard</code></pre>
  </li>
  <li><strong>Install Dependencies:</strong><br>
    <strong>Windows:</strong> Run <code>setup.bat</code>, which installs the necessary Python libraries and dependencies.<br>
    <strong>Other OS:</strong> Install the required packages manually, such as <code>playwright</code>, <code>openai</code>, <code>flask</code>, and any others specified in the project.<br><br>
    Additionally, ensure you have your OpenAI API key for tweet analysis.
  </li>
  <li><strong>Run the Application:</strong><br>
    Execute the start script:
    <pre><code>python start.py</code></pre>
  </li>
  <li><strong>Access the Dashboard:</strong><br>
    Open your web browser and navigate to <code>http://localhost:2001</code> to view the dashboard.
  </li>
</ol>

<h2>Usage</h2>

<ol>
  <li><strong>Select Date Range:</strong> Use the date range picker to select the desired period for analytics.</li>
  <li><strong>View Sentiment and Category Trends:</strong> Sentiment and category sections provide detailed analysis with distribution lists and charts.</li>
  <li><strong>Check Trending Topics:</strong> Displays topics based on tweet mentions.</li>
  <li><strong>Filter Tweets:</strong> Filter tweets based on sentiment or category for a more refined view.</li>
  <li><strong>Word Cloud:</strong> Check the word cloud for recommended accounts to help broaden your Twitter network.</li>
</ol>

<h2>Technologies Used</h2>

<ul>
  <li><strong>Backend</strong>: Python, Flask</li>
  <li><strong>Frontend</strong>: HTML, Tailwind CSS, Chart.js, D3.js</li>
  <li><strong>Data Extraction</strong>: Playwright for automated Twitter data extraction</li>
  <li><strong>Analysis</strong>: OpenAI API for sentiment and category analysis</li>
</ul>

<hr>
<p>This project aims to help users take control of their Twitter experience by providing objective insights. Whether you feel overwhelmed by negativity or stuck in an echo chamber, this dashboard offers a way to step back and evaluate your feed from a fresh perspective.</p>
