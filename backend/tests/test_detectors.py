"""Unit tests for code detectors"""
import pytest
from unittest.mock import Mock

from app.services.detectors.http_python import PythonHTTPDetector
from app.services.detectors.http_javascript import JavaScriptHTTPDetector
from app.services.detectors.http_java import JavaHTTPDetector
from app.services.detectors.kafka_python import PythonKafkaDetector
from app.services.detectors.kafka_java import JavaKafkaDetector
from app.services.detectors.kafka_node import NodeKafkaDetector


class TestPythonHTTPDetector:
    """Test suite for Python HTTP detector"""
    
    @pytest.fixture
    def detector(self):
        return PythonHTTPDetector()
    
    def test_detect_requests_get(self, detector):
        """Test detection of requests.get calls"""
        code = """
import requests

def get_user_data(user_id):
    response = requests.get(f'https://api.service.com/users/{user_id}')
    return response.json()
"""
        
        findings = detector.detect("src/user_service.py", code)
        
        assert len(findings) == 1
        finding = findings[0]
        assert finding["type"] == "http"
        assert finding["method"] == "GET"
        assert "users" in finding["url"]
        assert finding["source_file"] == "src/user_service.py"
    
    def test_detect_requests_post(self, detector):
        """Test detection of requests.post calls"""
        code = """
import requests

def create_order(order_data):
    response = requests.post(
        'https://payment-service.internal/api/orders',
        json=order_data,
        headers={'Authorization': 'Bearer token123'}
    )
    return response
"""
        
        findings = detector.detect("src/order_service.py", code)
        
        assert len(findings) == 1
        finding = findings[0]
        assert finding["type"] == "http"
        assert finding["method"] == "POST"
        assert "orders" in finding["url"]
        assert "Authorization" in finding.get("headers", {})
    
    def test_detect_httpx_calls(self, detector):
        """Test detection of httpx calls"""
        code = """
import httpx

async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get('http://auth-service:8080/api/validate')
        return response.json()
"""
        
        findings = detector.detect("src/auth_client.py", code)
        
        assert len(findings) >= 1
        # Should detect the httpx GET call
        urls = [f["url"] for f in findings]
        assert any("validate" in url for url in urls)
    
    def test_detect_urllib_requests(self, detector):
        """Test detection of urllib requests"""
        code = """
import urllib.request
import urllib.parse

def call_external_api():
    url = 'https://notification-service/api/send'
    data = urllib.parse.urlencode({'message': 'test'}).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    response = urllib.request.urlopen(req)
    return response.read()
"""
        
        findings = detector.detect("src/notification_client.py", code)
        
        assert len(findings) >= 1
        urls = [f["url"] for f in findings]
        assert any("send" in url for url in urls)
    
    def test_detect_no_http_calls(self, detector):
        """Test detection when no HTTP calls are present"""
        code = """
def calculate_sum(a, b):
    return a + b

def process_data(data):
    return [x * 2 for x in data]
"""
        
        findings = detector.detect("src/utils.py", code)
        
        assert len(findings) == 0
    
    def test_detect_multiple_calls(self, detector):
        """Test detection of multiple HTTP calls"""
        code = """
import requests

def get_user(user_id):
    return requests.get(f'https://api.service.com/users/{user_id}').json()

def get_orders(customer_id):
    return requests.get(f'https://order-service/api/customers/{customer_id}/orders').json()

def send_notification(message):
    return requests.post('https://notification-service/api/send', json={'message': message})
"""
        
        findings = detector.detect("src/user_service.py", code)
        
        assert len(findings) == 3
        
        methods = [f["method"] for f in findings]
        assert methods.count("GET") == 2
        assert methods.count("POST") == 1


class TestJavaScriptHTTPDetector:
    """Test suite for JavaScript HTTP detector"""
    
    @pytest.fixture
    def detector(self):
        return JavaScriptHTTPDetector()
    
    def test_detect_fetch_get(self, detector):
        """Test detection of fetch GET calls"""
        code = """
async function getUserData(userId) {
    const response = await fetch(`https://api.service.com/users/${userId}`);
    return response.json();
}
"""
        
        findings = detector.detect("src/userService.js", code)
        
        assert len(findings) == 1
        finding = findings[0]
        assert finding["type"] == "http"
        assert finding["method"] == "GET"
        assert "users" in finding["url"]
    
    def test_detect_axios_post(self, detector):
        """Test detection of axios POST calls"""
        code = """
import axios from 'axios';

async function createOrder(orderData) {
    const response = await axios.post('https://payment-service.internal/api/orders', orderData, {
        headers: {
            'Authorization': 'Bearer token123',
            'Content-Type': 'application/json'
        }
    });
    return response.data;
}
"""
        
        findings = detector.detect("src/orderService.js", code)
        
        assert len(findings) == 1
        finding = findings[0]
        assert finding["type"] == "http"
        assert finding["method"] == "POST"
        assert "orders" in finding["url"]
        assert "Authorization" in finding.get("headers", {})
    
    def test_detect_xmlhttprequest(self, detector):
        """Test detection of XMLHttpRequest calls"""
        code = """
function fetchUserData(userId) {
    const xhr = new XMLHttpRequest();
    xhr.open('GET', `https://auth-service/api/users/${userId}/status`);
    xhr.send();
    return new Promise((resolve) => {
        xhr.onload = () => resolve(JSON.parse(xhr.responseText));
    });
}
"""
        
        findings = detector.detect("src/authClient.js", code)
        
        assert len(findings) >= 1
        urls = [f["url"] for f in findings]
        assert any("users" in url and "status" in url for url in urls)
    
    def test_detect_node_http(self, detector):
        """Test detection of Node.js http module calls"""
        code = """
const http = require('http');

function callExternalService() {
    const data = JSON.stringify({message: 'test'});
    const options = {
        hostname: 'notification-service',
        port: 8080,
        path: '/api/send',
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': data.length
        }
    };
    
    const req = http.request(options, (res) => {
        console.log(`STATUS: ${res.statusCode}`);
        res.setEncoding('utf8');
        res.on('data', (chunk) => {
            console.log(`BODY: ${chunk}`);
        });
    });
    
    req.on('error', (e) => {
        console.error(`problem with request: ${e.message}`);
    });
    
    req.write(data);
    req.end();
}
"""
        
        findings = detector.detect("src/notificationClient.js", code)
        
        assert len(findings) >= 1
        urls = [f["url"] for f in findings]
        assert any("send" in url for url in urls)


class TestJavaHTTPDetector:
    """Test suite for Java HTTP detector"""
    
    @pytest.fixture
    def detector(self):
        return JavaHTTPDetector()
    
    def test_detect_okhttp_get(self, detector):
        """Test detection of OkHttp GET calls"""
        code = """
import okhttp3.OkHttpClient;
import okhttp3.Request;

public class UserService {
    private final OkHttpClient client = new OkHttpClient();
    
    public String getUserData(String userId) {
        Request request = new Request.Builder()
            .url("https://api.service.com/users/" + userId)
            .build();
            
        try (Response response = client.newCall(request).execute()) {
            return response.body().string();
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}
"""
        
        findings = detector.detect("src/UserService.java", code)
        
        assert len(findings) >= 1
        urls = [f["url"] for f in findings]
        assert any("users" in url for url in urls)
    
    def test_detect_resttemplate_post(self, detector):
        """Test detection of Spring RestTemplate POST calls"""
        code = """
import org.springframework.web.client.RestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;

@Service
public class OrderService {
    
    @Autowired
    private RestTemplate restTemplate;
    
    public OrderResponse createOrder(OrderRequest orderData) {
        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth("token123");
        
        HttpEntity<OrderRequest> entity = new HttpEntity<>(orderData, headers);
        
        ResponseEntity<OrderResponse> response = restTemplate.exchange(
            "https://payment-service.internal/api/orders",
            HttpMethod.POST,
            entity,
            OrderResponse.class
        );
        
        return response.getBody();
    }
}
"""
        
        findings = detector.detect("src/OrderService.java", code)
        
        assert len(findings) >= 1
        urls = [f["url"] for f in findings]
        assert any("orders" in url for url in urls)
    
    def test_detect_httpurlconnection(self, detector):
        """Test detection of HttpURLConnection calls"""
        code = """
import java.net.HttpURLConnection;
import java.net.URL;

public class NotificationService {
    
    public void sendNotification(String message) {
        try {
            URL url = new URL("https://notification-service/api/send");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setDoOutput(true);
            
            String jsonPayload = String.format("{\"message\": \"%s\"}", message);
            
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = jsonPayload.getBytes("utf-8");
                os.write(input, 0, input.length);
            }
            
            int responseCode = conn.getResponseCode();
            System.out.println("Response code: " + responseCode);
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
"""
        
        findings = detector.detect("src/NotificationService.java", code)
        
        assert len(findings) >= 1
        urls = [f["url"] for f in findings]
        assert any("send" in url for url in urls)


class TestKafkaDetectors:
    """Test suite for Kafka detectors"""
    
    @pytest.fixture
    def python_detector(self):
        return PythonKafkaDetector()
    
    @pytest.fixture
    def java_detector(self):
        return JavaKafkaDetector()
    
    @pytest.fixture
    def node_detector(self):
        return NodeKafkaDetector()
    
    def test_python_kafka_consumer(self, python_detector):
        """Test detection of Python Kafka consumers"""
        code = """
from kafka import KafkaConsumer
import json

def consume_user_events():
    consumer = KafkaConsumer(
        'user-events',
        'user-updates',
        bootstrap_servers=['kafka-broker:9092'],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='user-service-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    for message in consumer:
        process_user_event(message.value)
"""
        
        findings = python_detector.detect("src/user_consumer.py", code)
        
        assert len(findings) >= 2  # Should detect both topics
        topics = [f.get("topic") for f in findings if f.get("type") == "kafka"]
        assert "user-events" in topics
        assert "user-updates" in topics
    
    def test_python_kafka_producer(self, python_detector):
        """Test detection of Python Kafka producers"""
        code = """
from kafka import KafkaProducer
import json

def send_order_event(order_data):
    producer = KafkaProducer(
        bootstrap_servers=['kafka-broker:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=str.encode
    )
    
    future = producer.send('order-events', key=str(order_data['id']), value=order_data)
    result = future.get(timeout=10)
    
    return result
"""
        
        findings = python_detector.detect("src/order_producer.py", code)
        
        assert len(findings) >= 1
        topics = [f.get("topic") for f in findings if f.get("type") == "kafka"]
        assert "order-events" in topics
    
    def test_java_kafka_consumer(self, java_detector):
        """Test detection of Java Kafka consumers"""
        code = """
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.serialization.StringDeserializer;
import java.util.Properties;

@Service
public class UserEventConsumer {
    
    @EventListener
    public void consumeUserEvents() {
        Properties props = new Properties();
        props.put("bootstrap.servers", "kafka-broker:9092");
        props.put("group.id", "user-service-group");
        props.put("key.deserializer", StringDeserializer.class.getName());
        props.put("value.deserializer", StringDeserializer.class.getName());
        
        KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
        consumer.subscribe(Arrays.asList("user-events", "user-authentication"));
        
        while (true) {
            ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
            for (ConsumerRecord<String, String> record : records) {
                processUserEvent(record.value());
            }
        }
    }
}
"""
        
        findings = java_detector.detect("src/UserEventConsumer.java", code)
        
        assert len(findings) >= 2
        topics = [f.get("topic") for f in findings if f.get("type") == "kafka"]
        assert "user-events" in topics
        assert "user-authentication" in topics
    
    def test_node_kafka_consumer(self, node_detector):
        """Test detection of Node.js Kafka consumers"""
        code = """
const { Kafka } = require('kafkajs');

const kafka = new Kafka({
  clientId: 'notification-service',
  brokers: ['kafka-broker:9092']
});

const consumer = kafka.consumer({ groupId: 'notification-group' });

async function consumeOrderEvents() {
  await consumer.connect();
  await consumer.subscribe({ topics: ['order-events', 'order-updates'] });
  
  await consumer.run({
    eachMessage: async ({ topic, partition, message }) => {
      const value = message.value.toString();
      console.log({
        topic,
        partition,
        offset: message.offset,
        value
      });
      
      await processOrderEvent(JSON.parse(value));
    },
  });
}
"""
        
        findings = node_detector.detect("src/orderConsumer.js", code)
        
        assert len(findings) >= 2
        topics = [f.get("topic") for f in findings if f.get("type") == "kafka"]
        assert "order-events" in topics
        assert "order-updates" in topics
    
    def test_kafka_producer_pattern(self, python_detector):
        """Test detection of Kafka producer patterns"""
        code = """
import asyncio
from aiokafka import AIOKafkaProducer

async def send_notification(notification_data):
    producer = AIOKafkaProducer(
        bootstrap_servers='kafka-broker:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    await producer.start()
    try:
        await producer.send_and_wait('notification-events', notification_data)
    finally:
        await producer.stop()
"""
        
        findings = python_detector.detect("src/notification_producer.py", code)
        
        assert len(findings) >= 1
        topics = [f.get("topic") for f in findings if f.get("type") == "kafka"]
        assert "notification-events" in topics


class TestDetectorIntegration:
    """Test suite for detector integration scenarios"""
    
    @pytest.fixture
    def python_http_detector(self):
        return PythonHTTPDetector()
    
    @pytest.fixture
    def python_kafka_detector(self):
        return PythonKafkaDetector()
    
    def test_mixed_http_and_kafka_service(self, python_http_detector, python_kafka_detector):
        """Test detection in a service with both HTTP and Kafka"""
        code = """
import requests
from kafka import KafkaConsumer, KafkaProducer
import json

class UserService:
    def __init__(self):
        self.consumer = KafkaConsumer(
            'user-events',
            bootstrap_servers=['kafka-broker:9092'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        self.producer = KafkaProducer(
            bootstrap_servers=['kafka-broker:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
    
    def get_user_profile(self, user_id):
        response = requests.get(f'https://auth-service/api/users/{user_id}/profile')
        return response.json()
    
    def send_user_created_event(self, user_data):
        self.producer.send('user-created-events', user_data)
    
    def process_user_events(self):
        for message in self.consumer:
            self.handle_user_event(message.value)
"""
        
        # Test HTTP detection
        http_findings = python_http_detector.detect("src/user_service.py", code)
        assert len(http_findings) >= 1
        assert any(f["method"] == "GET" for f in http_findings)
        
        # Test Kafka detection
        kafka_findings = python_kafka_detector.detect("src/user_service.py", code)
        assert len(kafka_findings) >= 2  # Should detect both consumer and producer topics
        topics = [f.get("topic") for f in kafka_findings if f.get("type") == "kafka"]
        assert "user-events" in topics
        assert "user-created-events" in topics
    
    def test_complex_microservice_codebase(self, python_http_detector, python_kafka_detector):
        """Test detection in complex microservice code"""
        
        # Order service with multiple HTTP calls and Kafka topics
        order_service_code = """
from flask import Flask, request, jsonify
import requests
from kafka import KafkaProducer
import redis
import json

app = Flask(__name__)

@app.route('/orders', methods=['POST'])
def create_order():
    order_data = request.json
    
    # Call user service to validate user
    user_response = requests.get(f'https://user-service/api/users/{order_data["user_id"]}/validate')
    if not user_response.json()['valid']:
        return jsonify({'error': 'Invalid user'}), 400
    
    # Call payment service
    payment_response = requests.post(
        'https://payment-service/api/payments/process',
        json={'amount': order_data['amount'], 'user_id': order_data['user_id']},
        headers={'Authorization': f'Bearer {get_auth_token()}'}
    )
    
    # Create order in database
    order = save_order_to_db(order_data)
    
    # Send event to Kafka
    producer = KafkaProducer(bootstrap_servers=['kafka:9092'])
    producer.send('order-created', {
        'order_id': order.id,
        'user_id': order.user_id,
        'amount': order.amount,
        'status': 'created'
    })
    
    # Send notification
    requests.post(
        'https://notification-service/api/email',
        json={
            'to': order.user_email,
            'subject': 'Order Created',
            'body': f'Your order {order.id} has been created'
        }
    )
    
    return jsonify({'order_id': order.id, 'status': 'created'}), 201
"""
        
        # Test HTTP detection
        http_findings = python_http_detector.detect("src/order_service.py", order_service_code)
        assert len(http_findings) >= 4  # Multiple HTTP calls detected
        
        # Test Kafka detection
        kafka_findings = python_kafka_detector.detect("src/order_service.py", order_service_code)
        assert len(kafka_findings) >= 1
        
        topics = [f.get("topic") for f in kafka_findings if f.get("type") == "kafka"]
        assert "order-created" in topics
    
    def test_detector_edge_cases(self, python_http_detector):
        """Test detector edge cases and error handling"""
        
        # Test with malformed code
        malformed_code = """
import requests

def broken_function(
    # Missing closing parenthesis and other syntax errors
    response = requests.get('https://api.service.com/data'
    
    return response.json()
"""
        
        # Should not crash, should return empty findings or handle gracefully
        findings = python_http_detector.detect("src/broken.py", malformed_code)
        assert isinstance(findings, list)
        
        # Test with empty code
        empty_findings = python_http_detector.detect("src/empty.py", "")
        assert empty_findings == []
        
        # Test with non-code content
        text_findings = python_http_detector.detect("src/readme.txt", "This is not code")
        assert text_findings == []
    
    def test_detector_confidence_scoring(self, python_http_detector):
        """Test detector confidence scoring"""
        
        # High confidence: Clear HTTP call with all details
        high_confidence_code = """
import requests

response = requests.get(
    'https://payment-service.internal/api/validate-payment',
    params={'transaction_id': '12345'},
    headers={'Authorization': 'Bearer token123'},
    timeout=30
)
"""
        
        findings = python_http_detector.detect("src/payment_validator.py", high_confidence_code)
        assert len(findings) >= 1
        confidence = findings[0].get("confidence", 0)
        assert confidence > 0.7  # Should have high confidence
        
        # Lower confidence: Generic or unclear HTTP call
        low_confidence_code = """
import urllib.request

def call_service(url):
    return urllib.request.urlopen(url).read()
"""
        
        findings = python_http_detector.detect("src/generic_client.py", low_confidence_code)
        assert len(findings) >= 1
        confidence = findings[0].get("confidence", 0)
        # Might have lower confidence due to generic nature