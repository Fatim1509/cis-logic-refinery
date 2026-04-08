#!/usr/bin/env python3
"""
CIS Consensus Verification Engine

Implements weighted consensus verification using cosine similarity and performance tracking.
"""

import json
import logging
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import re

logger = logging.getLogger(__name__)

class ConsensusEngine:
    """Consensus verification engine for multi-source intelligence"""
    
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.encoder = None
        self.source_weights = {
            'reuters': 0.25,
            'investing.com': 0.20,
            'tradingeconomics': 0.20,
            'finviz': 0.20,
            'twitter': 0.15
        }
        self.performance_history = {}
        
        logger.info(f"⚖️ Initializing consensus engine with threshold {threshold}")
        self._load_encoder()
    
    def _load_encoder(self):
        """Load sentence transformer for embeddings"""
        try:
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Sentence encoder loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not load sentence encoder: {e}")
            self.encoder = None
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and extra whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common financial stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among', 'within', 'without', 'under', 'over', 'behind', 'beside', 'beneath', 'beyond', 'across', 'around', 'near', 'far', 'inside', 'outside', 'against', 'toward', 'towards', 'upon', 'off', 'down', 'out', 'away', 'back', 'forward', 'ahead', 'aside', 'apart', 'together', 'alone', 'here', 'there', 'everywhere', 'anywhere', 'somewhere', 'nowhere', 'when', 'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose', 'if', 'unless', 'until', 'while', 'since', 'as', 'because', 'although', 'though', 'however', 'therefore', 'thus', 'hence', 'moreover', 'furthermore', 'nevertheless', 'nonetheless', 'meanwhile', 'otherwise', 'instead', 'besides', 'also', 'too', 'either', 'neither', 'both', 'all', 'any', 'some', 'many', 'much', 'few', 'little', 'more', 'most', 'less', 'least', 'very', 'quite', 'rather', 'pretty', 'fairly', 'really', 'truly', 'certainly', 'definitely', 'probably', 'possibly', 'maybe', 'perhaps', 'surely', 'clearly', 'obviously', 'apparently', 'seemingly', 'supposedly', 'allegedly', 'reportedly', 'presumably', 'presumedly', 'assumedly', 'supposedly', 'reportedly', 'allegedly', 'apparently', 'seemingly', 'presumably', 'presumedly', 'assumedly'}
        
        words = text.split()
        words = [word for word in words if word not in stop_words]
        
        return ' '.join(words)
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts"""
        if not self.encoder:
            # Fallback: simple word overlap
            words1 = set(self.normalize_text(text1).split())
            words2 = set(self.normalize_text(text2).split())
            
            if not words1 or not words2:
                return 0.0
            
            intersection = words1.intersection(words2)
            union = words1.union(words2)
            
            return len(intersection) / len(union) if union else 0.0
        
        # Use sentence transformer
        try:
            embeddings = self.encoder.encode([text1, text2])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            return float(similarity)
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    def group_similar_items(self, items: List[Dict], text_field: str = 'title') -> List[List[int]]:
        """Group similar items together"""
        if not items:
            return []
        
        n = len(items)
        groups = []
        used = [False] * n
        
        for i in range(n):
            if used[i]:
                continue
            
            current_group = [i]
            current_text = items[i].get(text_field, '')
            
            for j in range(i + 1, n):
                if used[j]:
                    continue
                
                compare_text = items[j].get(text_field, '')
                similarity = self.calculate_similarity(current_text, compare_text)
                
                if similarity >= self.threshold:
                    current_group.append(j)
                    used[j] = True
            
            groups.append(current_group)
            used[i] = True
        
        return groups
    
    def calculate_source_score(self, source: str, historical_performance: Dict = None) -> float:
        """Calculate weighted score for a data source"""
        base_weight = self.source_weights.get(source, 0.1)
        
        if historical_performance and source in historical_performance:
            # Adjust weight based on historical accuracy
            accuracy = historical_performance[source].get('accuracy', 0.5)
            recent_accuracy = historical_performance[source].get('recent_accuracy', accuracy)
            
            # Weight recent performance more heavily
            adjusted_weight = base_weight * (0.6 * recent_accuracy + 0.4 * accuracy)
            return min(adjusted_weight, base_weight * 1.5)  # Cap at 1.5x base
        
        return base_weight
    
    def verify_consensus(self, items: List[Dict]) -> Dict:
        """Verify consensus across multiple sources"""
        if not items:
            return {'consensus': 'insufficient_data', 'confidence': 0.0}
        
        # Group similar items
        similar_groups = self.group_similar_items(items)
        
        # Analyze each group
        verified_items = []
        total_confidence = 0.0
        
        for group_idx, group in enumerate(similar_groups):
            if not group:
                continue
            
            group_items = [items[i] for i in group]
            
            # Calculate group consensus
            group_result = self._analyze_group_consensus(group_items)
            verified_items.append(group_result)
            total_confidence += group_result['confidence']
        
        # Overall consensus
        overall_confidence = total_confidence / len(similar_groups) if similar_groups else 0.0
        
        # Determine overall sentiment
        sentiments = [item.get('sentiment', 'neutral') for item in verified_items]
        sentiment_counts = {
            'positive': sentiments.count('positive'),
            'negative': sentiments.count('negative'),
            'neutral': sentiments.count('neutral')
        }
        
        # Majority sentiment
        majority_sentiment = max(sentiment_counts, key=sentiment_counts.get)
        
        return {
            'consensus': 'verified' if overall_confidence > 0.6 else 'weak',
            'confidence': overall_confidence,
            'sentiment': majority_sentiment,
            'verified_items': verified_items,
            'total_sources': len(items),
            'verified_groups': len(similar_groups),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _analyze_group_consensus(self, group_items: List[Dict]) -> Dict:
        """Analyze consensus within a group of similar items"""
        if not group_items:
            return {'consensus': 'empty', 'confidence': 0.0}
        
        # Calculate weighted scores
        total_score = 0.0
        total_weight = 0.0
        sentiments = []
        
        for item in group_items:
            source = item.get('source', 'unknown')
            confidence = item.get('confidence', 0.5)
            sentiment = item.get('sentiment', 'neutral')
            
            # Get source weight
            source_weight = self.calculate_source_score(source)
            
            # Calculate weighted confidence
            weighted_confidence = confidence * source_weight
            
            total_score += weighted_confidence
            total_weight += source_weight
            sentiments.append(sentiment)
        
        # Average confidence
        avg_confidence = total_score / total_weight if total_weight > 0 else 0.0
        
        # Majority sentiment
        sentiment_counts = {
            'positive': sentiments.count('positive'),
            'negative': sentiments.count('negative'),
            'neutral': sentiments.count('neutral')
        }
        majority_sentiment = max(sentiment_counts, key=sentiment_counts.get)
        
        return {
            'consensus': 'strong' if avg_confidence > 0.7 else 'weak',
            'confidence': avg_confidence,
            'sentiment': majority_sentiment,
            'items_count': len(group_items),
            'sources': list(set(item.get('source', 'unknown') for item in group_items))
        }
    
    def process_intelligence_batch(self, raw_data: Dict) -> Dict:
        """Process a batch of intelligence data"""
        logger.info(f"Processing intelligence batch with {len(raw_data)} sources")
        
        all_items = []
        
        # Flatten all items from different sources
        for source, source_data in raw_data.items():
            if isinstance(source_data, dict) and 'data' in source_data:
                items = source_data['data']
                if isinstance(items, list):
                    for item in items:
                        item['source'] = source
                        all_items.append(item)
        
        if not all_items:
            logger.warning("No items found in intelligence batch")
            return {'error': 'no_items_found'}
        
        # Verify consensus
        verification_result = self.verify_consensus(all_items)
        
        # Add processing metadata
        verification_result['processed_at'] = datetime.utcnow().isoformat()
        verification_result['total_items'] = len(all_items)
        
        logger.info(f"✅ Processed {len(all_items)} items, verified {verification_result['verified_groups']} groups")
        
        return verification_result

# Example usage
if __name__ == "__main__":
    engine = ConsensusEngine(threshold=0.85)
    
    # Example test data
    test_data = {
        'reuters': {
            'data': [
                {'title': 'Apple stock rises on strong earnings', 'sentiment': 'positive', 'confidence': 0.8},
                {'title': 'Tech sector shows growth', 'sentiment': 'positive', 'confidence': 0.7}
            ]
        },
        'finviz': {
            'data': [
                {'title': 'AAPL bullish momentum detected', 'sentiment': 'positive', 'confidence': 0.75},
                {'title': 'Technology stocks trending up', 'sentiment': 'positive', 'confidence': 0.65}
            ]
        }
    }
    
    result = engine.process_intelligence_batch(test_data)
    print(f"Consensus: {result['consensus']} (confidence: {result['confidence']:.3f})")
    print(f"Sentiment: {result['sentiment']}")