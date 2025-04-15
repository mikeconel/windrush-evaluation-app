# dashboard/utils/ai_analysis.py
from textblob import TextBlob
import pandas as pd

def sentiment_analysis(text_responses):
    sentiments = []
    for text in text_responses:
        analysis = TextBlob(text)
        sentiments.append({
            'text': text,
            'polarity': analysis.sentiment.polarity,
            'subjectivity': analysis.sentiment.subjectivity
        })
    return pd.DataFrame(sentiments)