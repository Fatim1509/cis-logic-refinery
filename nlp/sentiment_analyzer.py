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
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Multi-model sentiment analyzer using VADER and finBERT"""
    
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self.finbert_model = None
        self.finbert_tokenizer = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        logger.info(f"🧠 Initializing sentiment analyzer on {self.device}")
        self._load_finbert()
    
    def _load_finbert(self):
        """Load finBERT model for financial sentiment analysis"""
        try:
            model_name = "yiyanghkust/finbert-tone"
            self.finbert_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.finbert_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.finbert_model.to(self.device)
            self.finbert_model.eval()
            logger.info("✅ finBERT model loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not load finBERT model: {e}")
            self.finbert_model = None
    
    def analyze_vader(self, text: str) -> Dict:
        """Analyze sentiment using VADER"""
        scores = self.vader.polarity_scores(text)
        
        # Classify based on compound score
        if scores['compound'] >= 0.05:
            sentiment = 'positive'
        elif scores['compound'] <= -0.05:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'confidence': abs(scores['compound']),
            'scores': scores,
            'model': 'vader'
        }
    
    def analyze_finbert(self, text: str) -> Dict:
        """Analyze sentiment using finBERT"""
        if self.finbert_model is None:
            return {'error': 'finBERT model not available'}
        
        try:
            # Tokenize input
            inputs = self.finbert_tokenizer(
                text, 
                return_tensors="pt", 
                max_length=512, 
                truncation=True, 
                padding=True
            ).to(self.device)
            
            # Get model predictions
            with torch.no_grad():
                outputs = self.finbert_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # Convert to probabilities
            probs = predictions[0].cpu().numpy()
            
            # Map to sentiment labels
            labels = ['negative', 'neutral', 'positive']
            sentiment_idx = np.argmax(probs)
            sentiment = labels[sentiment_idx]
            confidence = float(probs[sentiment_idx])
            
            return {
                'sentiment': sentiment,
                'confidence': confidence,
                'scores': {label: float(prob) for label, prob in zip(labels, probs)},
                'model': 'finbert'
            }
            
        except Exception as e:
            logger.error(f"finBERT analysis failed: {e}")
            return {'error': f'finBERT analysis failed: {e}'}
    
    def analyze_text(self, text: str, use_both: bool = True) -> Dict:
        """Analyze text using both VADER and finBERT"""
        if not text or len(text.strip()) < 10:
            return {'error': 'Text too short for analysis'}
        
        results = {}
        
        # VADER analysis
        vader_result = self.analyze_vader(text)
        results['vader'] = vader_result
        
        # finBERT analysis
        if self.finbert_model:
            finbert_result = self.analyze_finbert(text)
            results['finbert'] = finbert_result
        
        # Consensus analysis if both models available
        if use_both and 'finbert' in results and 'error' not in results['finbert']:
            consensus = self._calculate_consensus(results['vader'], results['finbert'])
            results['consensus'] = consensus
        
        results['text_length'] = len(text)
        results['analyzed_at'] = datetime.utcnow().isoformat()
        
        return results
    
    def _calculate_consensus(self, vader_result: Dict, finbert_result: Dict) -> Dict:
        """Calculate consensus between VADER and finBERT"""
        vader_sentiment = vader_result['sentiment']
        finbert_sentiment = finbert_result['sentiment']
        
        # Simple consensus logic
        if vader_sentiment == finbert_sentiment:
            consensus_sentiment = vader_sentiment
            confidence = (vader_result['confidence'] + finbert_result['confidence']) / 2
        else:
            # Weight finBERT higher for financial text
            consensus_sentiment = finbert_sentiment
            confidence = finbert_result['confidence'] * 0.7 + vader_result['confidence'] * 0.3
        
        return {
            'sentiment': consensus_sentiment,
            'confidence': confidence,
            'agreement': vader_sentiment == finbert_sentiment,
            'method': 'weighted_consensus'
        }
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """Analyze multiple texts"""
        results = []
        for i, text in enumerate(texts):
            logger.info(f"Analyzing text {i+1}/{len(texts)}")
            result = self.analyze_text(text)
            results.append(result)
        return results
    
    def get_model_info(self) -> Dict:
        """Get information about loaded models"""
        return {
            'vader_available': True,
            'finbert_available': self.finbert_model is not None,
            'device': str(self.device),
            'models_loaded_at': datetime.utcnow().isoformat()
        }

# Example usage
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()
    
    # Test texts
    test_texts = [
        "Apple reported strong earnings beating expectations with revenue up 15%",
        "Tesla stock crashes after disappointing delivery numbers",
        "Microsoft announces new AI initiatives with mixed market reaction"
    ]
    
    for text in test_texts:
        print(f"\n📝 Text: {text[:60]}...")
        results = analyzer.analyze_text(text)
        
        if 'consensus' in results:
            consensus = results['consensus']
            print(f"🎯 Consensus: {consensus['sentiment']} (confidence: {consensus['confidence']:.3f})")
        
        print(f"📊 VADER: {results['vader']['sentiment']} ({results['vader']['confidence']:.3f})")
        
        if 'finbert' in results and 'error' not in results['finbert']:
            print(f"🧠 finBERT: {results['finbert']['sentiment']} ({results['finbert']['confidence']:.3f})")