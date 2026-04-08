#!/usr/bin/env python3
"""
CIS Sentiment Analyzer

Analyzes financial text using VADER and finBERT models for sentiment classification.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple
import numpy as np

# VADER sentiment analysis
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    logging.warning("VADER not available, using fallback")

# Financial BERT
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Multi-model sentiment analyzer for financial text"""
    
    def __init__(self, use_vader=True, use_finbert=True):
        self.use_vader = use_vader and VADER_AVAILABLE
        self.use_finbert = use_finbert
        
        # Initialize VADER
        if self.use_vader:
            self.vader_analyzer = SentimentIntensityAnalyzer()
            logger.info("✅ VADER analyzer initialized")
        
        # Initialize finBERT
        if self.use_finbert:
            try:
                self.finbert_pipeline = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    tokenizer="ProsusAI/finbert",
                    max_length=512,
                    truncation=True
                )
                logger.info("✅ FinBERT pipeline initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize FinBERT: {e}")
                self.use_finbert = False
    
    def analyze_vader(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using VADER"""
        if not self.use_vader:
            return {'compound': 0.0, 'pos': 0.0, 'neu': 0.0, 'neg': 0.0}
        
        try:
            scores = self.vader_analyzer.polarity_scores(text)
            return scores
        except Exception as e:
            logger.error(f"VADER analysis failed: {e}")
            return {'compound': 0.0, 'pos': 0.0, 'neu': 0.0, 'neg': 0.0}
    
    def analyze_finbert(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using FinBERT"""
        if not self.use_finbert:
            return {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}
        
        try:
            # Truncate text if too long
            if len(text) > 500:
                text = text[:500] + "..."
            
            result = self.finbert_pipeline(text)[0]
            label = result['label'].lower()
            score = result['score']
            
            # Convert to probabilities
            if label == 'positive':
                return {'positive': score, 'negative': (1-score)/2, 'neutral': (1-score)/2}
            elif label == 'negative':
                return {'positive': (1-score)/2, 'negative': score, 'neutral': (1-score)/2}
            else:  # neutral
                return {'positive': (1-score)/2, 'negative': (1-score)/2, 'neutral': score}
                
        except Exception as e:
            logger.error(f"FinBERT analysis failed: {e}")
            return {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}
    
    def combine_sentiments(self, vader_scores: Dict, finbert_scores: Dict) -> Dict[str, float]:
        """Combine VADER and FinBERT scores"""
        
        # Normalize VADER compound score to 0-1 range
        vader_normalized = (vader_scores['compound'] + 1) / 2
        
        # Extract FinBERT probabilities
        finbert_positive = finbert_scores.get('positive', 0.33)
        finbert_negative = finbert_scores.get('negative', 0.33)
        finbert_neutral = finbert_scores.get('neutral', 0.34)
        
        # Weighted combination (60% VADER, 40% FinBERT for financial domain)
        combined_positive = (vader_normalized * 0.6) + (finbert_positive * 0.4)
        combined_negative = ((1 - vader_normalized) * 0.6) + (finbert_negative * 0.4)
        combined_neutral = finbert_neutral * 0.4  # FinBERT neutral only
        
        # Normalize to ensure they sum to 1
        total = combined_positive + combined_negative + combined_neutral
        if total > 0:
            combined_positive /= total
            combined_negative /= total
            combined_neutral /= total
        
        return {
            'positive': combined_positive,
            'negative': combined_negative,
            'neutral': combined_neutral,
            'confidence': max(combined_positive, combined_negative, combined_neutral)
        }
    
    def classify_sentiment(self, combined_scores: Dict) -> str:
        """Classify overall sentiment"""
        positive = combined_scores['positive']
        negative = combined_scores['negative']
        neutral = combined_scores['neutral']
        
        # Determine dominant sentiment
        if positive > negative and positive > neutral:
            return 'positive'
        elif negative > positive and negative > neutral:
            return 'negative'
        else:
            return 'neutral'
    
    def analyze_text(self, text: str) -> Dict:
        """Analyze text sentiment using all available models"""
        
        if not text or len(text.strip()) == 0:
            return {
                'text': text,
                'sentiment': 'neutral',
                'confidence': 0.5,
                'vader_scores': self.analyze_vader(text),
                'finbert_scores': self.analyze_finbert(text),
                'combined_scores': {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34, 'confidence': 0.5}
            }
        
        # Analyze with VADER
        vader_scores = self.analyze_vader(text)
        
        # Analyze with FinBERT
        finbert_scores = self.analyze_finbert(text)
        
        # Combine scores
        combined_scores = self.combine_sentiments(vader_scores, finbert_scores)
        
        # Classify overall sentiment
        sentiment_label = self.classify_sentiment(combined_scores)
        
        result = {
            'text': text[:200] + "..." if len(text) > 200 else text,  # Truncate for storage
            'sentiment': sentiment_label,
            'confidence': combined_scores['confidence'],
            'vader_scores': vader_scores,
            'finbert_scores': finbert_scores,
            'combined_scores': combined_scores,
            'analyzed_at': datetime.utcnow().isoformat()
        }
        
        return result
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """Analyze multiple texts"""
        results = []
        for text in texts:
            result = self.analyze_text(text)
            results.append(result)
        return results
    
    def get_sentiment_summary(self, results: List[Dict]) -> Dict:
        """Get summary statistics for batch analysis"""
        if not results:
            return {'total': 0, 'positive': 0, 'negative': 0, 'neutral': 0, 'avg_confidence': 0}
        
        total = len(results)
        positive = sum(1 for r in results if r['sentiment'] == 'positive')
        negative = sum(1 for r in results if r['sentiment'] == 'negative')
        neutral = sum(1 for r in results if r['sentiment'] == 'neutral')
        avg_confidence = sum(r['confidence'] for r in results) / total
        
        return {
            'total': total,
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'positive_pct': (positive / total) * 100,
            'negative_pct': (negative / total) * 100,
            'neutral_pct': (neutral / total) * 100,
            'avg_confidence': avg_confidence
        }

# Example usage
def main():
    analyzer = SentimentAnalyzer()
    
    # Test texts
    texts = [
        "The stock market is crashing! Sell everything now!",
        "Great earnings report, company beating expectations.",
        "Market remains flat with no significant movement.",
        "Bitcoin surges to new all-time highs amid institutional adoption."
    ]
    
    # Analyze batch
    results = analyzer.analyze_batch(texts)
    
    # Print results
    for i, result in enumerate(results):
        print(f"\nText {i+1}: {result['text']}")
        print(f"Sentiment: {result['sentiment']} (confidence: {result['confidence']:.3f})")
        print(f"VADER compound: {result['vader_scores']['compound']:.3f}")
        print(f"FinBERT: +{result['finbert_scores']['positive']:.3f} -{result['finbert_scores']['negative']:.3f}")
    
    # Summary
    summary = analyzer.get_sentiment_summary(results)
    print(f"\n📊 Summary: {summary['positive']} positive, {summary['negative']} negative, {summary['neutral']} neutral")
    print(f"Average confidence: {summary['avg_confidence']:.3f}")

if __name__ == "__main__":
    main()