"""Python Kafka detector"""
import re
from typing import List, Dict, Any


class PythonKafkaDetector:
    """Detects Kafka producers and consumers in Python code"""
    
    def __init__(self):
        # Producer patterns
        self.producer_patterns = [
            (r"producer\.send\(['\"]([^'\"]+)['\"]", "producer"),
            (r"KafkaProducer\([^)]*\)\.send\(['\"]([^'\"]+)['\"]", "kafka-python"),
            (r"confluent_kafka\.Producer\([^)]*\)\.produce\(['\"]([^'\"]+)['\"]", "confluent-kafka"),
        ]
        
        # Consumer patterns
        self.consumer_patterns = [
            (r"consumer\.subscribe\(\[['\"]([^'\"]+)['\"]", "consumer"),
            (r"KafkaConsumer\(['\"]([^'\"]+)['\"]", "kafka-python"),
            (r"confluent_kafka\.Consumer\([^)]*\)\.subscribe\(\[['\"]([^'\"]+)['\"]", "confluent-kafka"),
        ]
    
    def detect(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Detect Kafka producers and consumers"""
        findings = []
        
        # Detect producers
        for pattern, library in self.producer_patterns:
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
        
        # Detect consumers
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
                    "confidence": 0.85,
                })
        
        return findings

