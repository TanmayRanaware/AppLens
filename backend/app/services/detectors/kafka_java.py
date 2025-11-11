"""Java Kafka detector"""
import re
from typing import List, Dict, Any


class JavaKafkaDetector:
    """Detects Kafka producers and consumers in Java code"""
    
    def __init__(self):
        # Producer patterns
        self.producer_patterns = [
            (r"kafkaProducer\.send\([^)]*['\"]([^'\"]+)['\"]", "KafkaProducer"),
            (r"@KafkaListener\(topics\s*=\s*['\"]([^'\"]+)['\"]", "SpringKafka"),
        ]
        
        # Consumer patterns
        self.consumer_patterns = [
            (r"@KafkaListener\(topics\s*=\s*['\"]([^'\"]+)['\"]", "SpringKafka"),
            (r"consumer\.subscribe\([^)]*['\"]([^'\"]+)['\"]", "KafkaConsumer"),
        ]
    
    def detect(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Detect Kafka producers and consumers"""
        findings = []
        
        # Detect consumers (annotations)
        for pattern, library in self.consumer_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                topic = match.group(1)
                line_num = content[:match.start()].count("\n") + 1
                
                findings.append({
                    "type": "Kafka",
                    "direction": "consumer",
                    "topic": topic,
                    "library": library,
                    "file": file_path,
                    "line": line_num,
                    "confidence": 0.90,
                })
        
        # Detect producers
        for pattern, library in self.producer_patterns:
            if library == "SpringKafka":
                continue  # Already handled
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                topic = match.group(1)
                line_num = content[:match.start()].count("\n") + 1
                
                findings.append({
                    "type": "Kafka",
                    "direction": "producer",
                    "topic": topic,
                    "library": library,
                    "file": file_path,
                    "line": line_num,
                    "confidence": 0.85,
                })
        
        return findings

