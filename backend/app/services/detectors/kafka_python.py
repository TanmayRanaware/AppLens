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
            # Match KafkaConsumer("topic" on same line
            (r"KafkaConsumer\(\s*['\"]([^'\"]+)['\"]", "kafka-python"),
            # Match KafkaConsumer( and extract topic from next lines (handles multi-line)
            # Pattern: KafkaConsumer(\n    "topic-name",\n    ...
            (r"KafkaConsumer\(", "kafka-python-multiline"),
            # Also match KafkaConsumer("topic", ...) with newlines between
            (r"KafkaConsumer\(\s*\n\s*['\"]([^'\"]+)['\"]", "kafka-python"),
            (r"confluent_kafka\.Consumer\([^)]*\)\.subscribe\(\[['\"]([^'\"]+)['\"]", "confluent-kafka"),
        ]
    
    def detect(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Detect Kafka producers and consumers"""
        findings = []
        
        # Detect producers
        for pattern, library in self.producer_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                if len(match.groups()) > 0:
                    topic = match.group(1)
                else:
                    # Try to extract topic from next line
                    match_end = match.end()
                    next_lines = content[match_end:match_end+200]  # Look ahead 200 chars
                    topic_match = re.search(r"['\"]([^'\"]+)['\"]", next_lines)
                    if topic_match:
                        topic = topic_match.group(1)
                    else:
                        continue
                
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
        
        # Detect consumers - handle multi-line KafkaConsumer calls
        for pattern, library in self.consumer_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                topic = None
                if len(match.groups()) > 0:
                    topic = match.group(1)
                elif library == "kafka-python-multiline":
                    # For KafkaConsumer( pattern, extract topic from next lines
                    match_end = match.end()
                    next_lines = content[match_end:match_end+500]  # Look ahead 500 chars for multi-line
                    # Look for quoted string (topic name) - usually first quoted string after opening paren
                    # Skip whitespace and newlines
                    topic_match = re.search(r"['\"]([a-z0-9_-]+)['\"]", next_lines)
                    if topic_match:
                        topic = topic_match.group(1)
                else:
                    continue
                
                if not topic:
                    continue
                
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

