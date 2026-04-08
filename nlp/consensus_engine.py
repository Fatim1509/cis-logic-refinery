#!/usr/bin/env python3
"""
CIS Consensus Verification Engine

Implements weighted consensus algorithm and deduplication for multi-source validation.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class ConsensusEngine:
    """Multi-source consensus verification with weighted performance algorithm"""
    
    def __init__(self, config_path="config/weights.json"):
        self.config_path = config_path
        self.weights = self.load_weights()
        self.similarity_threshold = 0.85  # Cosine similarity threshold for deduplication
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
        # Historical performance tracking
        self.performance_history = self.load_performance_history()
        
    def load_weights(self) -> Dict[str, float]:
        """Load source weights configuration"""
        default_weights = {
            'reuters': 0.25,
            'investing': 0.20,
            'tradingeconomics': 0.20,
            'finviz': 0.20,
            'twitter': 0.15
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    weights = json.load(f)
                logger.info(f"✅ Loaded weights from {self.config_path}")
                return weights
        except Exception as e:
            logger.warning(f"⚠️ Could not load weights, using defaults: {e}")
        
        return default_weights
    
    def load_performance_history(self) -> Dict[str, List[float]]:
        """Load historical performance data"""
        history_file = "data/performance_history.json"
        
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    history = json.load(f)
                logger.info(f"✅ Loaded performance history from {history_file}")
                return history
        except Exception as e:
            logger.warning(f"⚠️ Could not load performance history: {e}")
        
        # Return empty history for each source
        return {source: [] for source in self.weights.keys()}
    
    def calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts"""
        try:
            # Vectorize texts
            tfidf_matrix = self.vectorizer.fit_transform([text1, text2])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on title similarity"""
        if not articles:
            return []
        
        logger.info(f"🔍 Deduplicating {len(articles)} articles...")
        
        unique_articles = []
        seen_titles = []
        
        for article in articles:
            title = article.get('title', '')
            if not title:
                continue
            
            # Check similarity with existing titles
            is_duplicate = False
            for seen_title in seen_titles:
                similarity = self.calculate_cosine_similarity(title, seen_title)
                if similarity > self.similarity_threshold:
                    is_duplicate = True
                    logger.debug(f"🔄 Duplicate detected (similarity: {similarity:.3f}): {title[:50]}...")
                    break
            
            if not is_duplicate:
                unique_articles.append(article)
                seen_titles.append(title)
        
        removed_count = len(articles) - len(unique_articles)
        logger.info(f"✅ Removed {removed_count} duplicates, {len(unique_articles)} unique articles remaining")
        
        return unique_articles
    
    def calculate_weighted_consensus(self, articles: List[Dict]) -> Dict:
        """Calculate weighted consensus score based on source reliability"""
        if not articles:
            return {'consensus_score': 0.0, 'recommendation': 'NEUTRAL', 'confidence': 0.0}
        
        # Group articles by sentiment
        sentiment_groups = {
            'positive': [],
            'negative': [],
            'neutral': []
        }
        
        for article in articles:
            sentiment = article.get('sentiment', 'neutral')
            source = article.get('source', 'unknown')
            confidence = article.get('confidence', 0.5)
            
            # Apply source weight
            weight = self.weights.get(source, 0.1)
            weighted_confidence = confidence * weight
            
            article_data = {
                'article': article,
                'weight': weight,
                'weighted_confidence': weighted_confidence
            }
            
            if sentiment in sentiment_groups:
                sentiment_groups[sentiment].append(article_data)
        
        # Calculate weighted scores for each sentiment
        scores = {}
        for sentiment, group in sentiment_groups.items():
            if group:
                # Sum of weighted confidences
                total_score = sum(item['weighted_confidence'] for item in group)
                # Normalize by number of articles and total possible weight
                normalized_score = total_score / len(group) if group else 0
                scores[sentiment] = normalized_score
            else:
                scores[sentiment] = 0.0
        
        # Determine dominant sentiment
        dominant_sentiment = max(scores, key=scores.get)
        consensus_score = scores[dominant_sentiment]
        
        # Calculate overall confidence
        total_articles = len(articles)
        avg_confidence = sum(article.get('confidence', 0.5) for article in articles) / total_articles if total_articles > 0 else 0
        
        # Consensus confidence considers both score magnitude and number of sources
        confidence = min(consensus_score * avg_confidence * (1 + total_articles * 0.1), 1.0)
        
        # Generate recommendation
        if consensus_score > 0.7 and confidence > 0.6:
            recommendation = 'STRONG_BUY' if dominant_sentiment == 'positive' else 'STRONG_SELL'
        elif consensus_score > 0.5 and confidence > 0.4:
            recommendation = 'BUY' if dominant_sentiment == 'positive' else 'SELL'
        else:
            recommendation = 'NEUTRAL'
        
        return {
            'consensus_score': consensus_score,
            'dominant_sentiment': dominant_sentiment,
            'recommendation': recommendation,
            'confidence': confidence,
            'source_breakdown': {
                'positive_count': len(sentiment_groups['positive']),
                'negative_count': len(sentiment_groups['negative']),
                'neutral_count': len(sentiment_groups['neutral']),
                'positive_score': scores['positive'],
                'negative_score': scores['negative'],
                'neutral_score': scores['neutral']
            }
        }
    
    def update_performance_history(self, source: str, accuracy: float):
        """Update historical performance for adaptive weighting"""
        if source not in self.performance_history:
            self.performance_history[source] = []
        
        self.performance_history[source].append(accuracy)
        
        # Keep only last 100 entries
        if len(self.performance_history[source]) > 100:
            self.performance_history[source] = self.performance_history[source][-100:]
    
    def calculate_adaptive_weights(self) -> Dict[str, float]:
        """Calculate weights based on historical performance"""
        adaptive_weights = {}
        
        for source, accuracies in self.performance_history.items():
            if accuracies:
                # Calculate average accuracy
                avg_accuracy = np.mean(accuracies[-20:])  # Last 20 entries
                adaptive_weights[source] = avg_accuracy
            else:
                # Use default weight if no history
                adaptive_weights[source] = self.weights.get(source, 0.1)
        
        # Normalize weights to sum to 1.0
        total_weight = sum(adaptive_weights.values())
        if total_weight > 0:
            for source in adaptive_weights:
                adaptive_weights[source] = adaptive_weights[source] / total_weight
        
        return adaptive_weights
    
    def verify_consensus(self, raw_data: Dict) -> Dict:
        """Main consensus verification method"""
        logger.info("⚖️ Starting consensus verification...")
        
        # Collect all articles from all sources
        all_articles = []
        
        for source, data in raw_data.items():
            if isinstance(data, dict) and 'data' in data:
                articles = data['data']
                if isinstance(articles, list):
                    for article in articles:
                        article['source'] = source
                        all_articles.append(article)
        
        logger.info(f"📊 Processing {len(all_articles)} articles from {len(raw_data)} sources")
        
        # Deduplicate articles
        unique_articles = self.deduplicate_articles(all_articles)
        
        # Calculate weighted consensus
        consensus_result = self.calculate_weighted_consensus(unique_articles)
        
        # Add verification metadata
        verification_result = {
            'timestamp': datetime.utcnow().isoformat(),
            'input_articles': len(all_articles),
            'unique_articles': len(unique_articles),
            'sources_analyzed': list(raw_data.keys()),
            'consensus': consensus_result,
            'weights_used': self.weights,
            'similarity_threshold': self.similarity_threshold
        }
        
        logger.info(f"✅ Consensus verification completed")
        logger.info(f"   Recommendation: {consensus_result['recommendation']}")
        logger.info(f"   Confidence: {consensus_result['confidence']:.3f}")
        logger.info(f"   Dominant sentiment: {consensus_result['dominant_sentiment']}")
        
        return verification_result
    
    def save_verification_result(self, result: Dict, filename: str = None):
        """Save verification result to file"""
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"data/consensus_verification_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info(f"💾 Verification result saved to {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to save verification result: {e}")

# Example usage
def main():
    # Mock data for testing
    mock_data = {
        'reuters': {
            'data': [
                {'title': 'Stock market rises on positive earnings', 'sentiment': 'positive', 'confidence': 0.8},
                {'title': 'Tech stocks surge ahead', 'sentiment': 'positive', 'confidence': 0.7}
            ]
        },
        'investing': {
            'data': [
                {'title': 'Market outlook remains bullish', 'sentiment': 'positive', 'confidence': 0.75},
                {'title': 'Investors optimistic about growth', 'sentiment': 'positive', 'confidence': 0.65}
            ]
        },
        'finviz': {
            'data': [
                {'title': 'Bullish sentiment dominates market', 'sentiment': 'positive', 'confidence': 0.9},
                {'title': 'Stocks continue upward trend', 'sentiment': 'positive', 'confidence': 0.8}
            ]
        }
    }
    
    # Initialize consensus engine
    engine = ConsensusEngine()
    
    # Verify consensus
    result = engine.verify_consensus(mock_data)
    
    # Print results
    print(f"Recommendation: {result['consensus']['recommendation']}")
    print(f"Confidence: {result['consensus']['confidence']:.3f}")
    print(f"Dominant sentiment: {result['consensus']['dominant_sentiment']}")
    
    # Save result
    engine.save_verification_result(result)

if __name__ == "__main__":
    main()