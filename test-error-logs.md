# Test Error Logs for Error Analyzer

## Error Log 1: User Service - Database Connection Failure

```
[2025-01-15 18:45:23.891] ERROR user-service - Critical service failure: User validation endpoint crashed
Traceback (most recent call last):
  File "/app/user-service/app.py", line 102, in validate_user
    if user_id not in users_db:
  File "/usr/local/lib/python3.11/site-packages/fastapi/routing.py", line 234, in app
    raise RuntimeError("Database connection lost - users_db is None")
RuntimeError: Database connection lost - users_db is None

Service: user-service
Endpoint: POST /users/{user_id}/validate
Status: 500 Internal Server Error
Timestamp: 2025-01-15T18:45:23.891Z
Error: Database connection lost - users_db is None
```

---

## Error Log 2: Payment Service - Payment Processing Failure

```
[2025-01-15 19:20:33.789] ERROR payment-service - Payment processing failed
Traceback (most recent call last):
  File "/app/payment-service/payment_handler.py", line 87, in process_payment
    if payment_amount <= 0:
AttributeError: 'NoneType' object has no attribute '__le__'

Service: payment-service
Endpoint: POST /payments/process
Status: 500 Internal Server Error
Timestamp: 2025-01-15T19:20:33.789Z
Error: Payment amount validation failed - payment_amount is None due to missing request body parsing
```

---

## Error Log 3: Order Service - Inventory Reservation Failure

```
[2025-01-15 20:15:12.456] ERROR order-service - Order creation failed
Traceback (most recent call last):
  File "/app/order-service/order_processor.py", line 145, in create_order
    response = httpx.post(f"{INVENTORY_SERVICE_URL}/inventory/{item.product_id}/reserve", json=reserve_data)
  File "/usr/local/lib/python3.11/site-packages/httpx/_client.py", line 1876, in post
    return self.request("POST", url, **kwargs)
  File "/usr/local/lib/python3.11/site-packages/httpx/_client.py", line 1547, in request
    response = self.send(request, auth=auth, follow_redirects=follow_redirects)
  File "/usr/local/lib/python3.11/site-packages/httpx/_client.py", line 1636, in send
    response = self._send_handling_auth(request, auth)
httpx.ConnectTimeout: Connection timeout to inventory-service

Service: order-service
Endpoint: POST /orders
Status: 500 Internal Server Error
Timestamp: 2025-01-15T20:15:12.456Z
Error: Failed to reserve inventory - inventory-service is not responding
```

---

## Error Log 4: Notification Service - Email Delivery Failure

```
[2025-01-15 21:30:45.123] ERROR notification-service - Email notification delivery failed
Traceback (most recent call last):
  File "/app/notification-service/email_sender.py", line 145, in send_email
    smtp_server.sendmail(from_addr, to_addr, message)
ConnectionError: SMTP server connection timeout - unable to reach mail server

Service: notification-service
Endpoint: POST /notifications/email
Status: 500 Internal Server Error
Timestamp: 2025-01-15T21:30:45.123Z
Error: Email service unavailable - SMTP server at smtp.example.com:587 is not responding
```

---

## Error Log 5: Cart Service - Product Service Connection Error

```
[2025-01-15 22:45:56.789] ERROR cart-service - Failed to fetch product details
Traceback (most recent call last):
  File "/app/cart-service/cart_manager.py", line 92, in add_to_cart
    product = await httpx.get(f"{PRODUCT_SERVICE_URL}/products/{item.product_id}")
  File "/usr/local/lib/python3.11/site-packages/httpx/_client.py", line 1621, in get
    return self.request("GET", url, **kwargs)
httpx.HTTPStatusError: 503 Service Unavailable

Service: cart-service
Endpoint: POST /cart/add
Status: 500 Internal Server Error
Timestamp: 2025-01-15T22:45:56.789Z
Error: Product service returned 503 - service unavailable
```

---

## Error Log 6: Recommendation Service - Kafka Consumer Error

```
[2025-01-15 23:10:12.345] ERROR recommendation-service - Kafka consumer error
Traceback (most recent call last):
  File "/app/recommendation-service/kafka_consumer.py", line 78, in consume_events
    for message in consumer:
  File "/usr/local/lib/python3.11/site-packages/kafka/consumer/group.py", line 1205, in __iter__
    return self.next()
kafka.errors.KafkaTimeoutError: Timeout waiting for message from topic 'user-events'

Service: recommendation-service
Kafka Topic: user-events
Status: 500 Internal Server Error
Timestamp: 2025-01-15T23:10:12.345Z
Error: Kafka consumer timeout - no messages received from user-events topic
```

---

## Error Log 7: Inventory Service - Stock Update Failure

```
[2025-01-16 08:30:22.567] ERROR inventory-service - Stock update failed
Traceback (most recent call last):
  File "/app/inventory-service/stock_manager.py", line 134, in update_stock
    if new_quantity < 0:
TypeError: '<' not supported between instances of 'NoneType' and 'int'

Service: inventory-service
Endpoint: PUT /inventory/{product_id}/stock
Status: 500 Internal Server Error
Timestamp: 2025-01-16T08:30:22.567Z
Error: Stock quantity validation failed - new_quantity is None
```

---

## Error Log 8: User Service - Authentication Failure

```
[2025-01-16 09:15:45.890] ERROR user-service - User authentication failed
Traceback (most recent call last):
  File "/app/user-service/auth.py", line 156, in authenticate_user
    if not verify_password(password, user.hashed_password):
  File "/app/user-service/auth.py", line 89, in verify_password
    return bcrypt.checkpw(password.encode(), hashed_password)
AttributeError: 'NoneType' object has no attribute 'encode'

Service: user-service
Endpoint: POST /users/login
Status: 401 Unauthorized
Timestamp: 2025-01-16T09:15:45.890Z
Error: Password verification failed - password is None
```

---

## Quick Copy-Paste Examples

### Simple User Service Error:
```
[2025-01-15 18:45:23.891] ERROR user-service - User validation endpoint failed
Traceback (most recent call last):
  File "/app/user-service/app.py", line 102, in validate_user
    if user_id not in users_db:
TypeError: 'NoneType' object is not subscriptable
Service: user-service
Endpoint: POST /users/{user_id}/validate
Status: 500 Internal Server Error
Timestamp: 2025-01-15T18:45:23.891Z
Error: Database connection lost - users_db is None
```

### Payment Service Error:
```
[2025-01-15 19:20:33.789] ERROR payment-service - Payment processing failed
Traceback (most recent call last):
  File "/app/payment-service/payment_handler.py", line 87, in process_payment
    if payment_amount <= 0:
AttributeError: 'NoneType' object has no attribute '__le__'
Service: payment-service
Endpoint: POST /payments/process
Status: 500 Internal Server Error
Timestamp: 2025-01-15T19:20:33.789Z
Error: Payment amount validation failed - payment_amount is None
```

### Order Service with Multiple Dependencies:
```
[2025-01-15 20:15:12.456] ERROR order-service - Order creation failed
Traceback (most recent call last):
  File "/app/order-service/order_processor.py", line 145, in create_order
    response = httpx.post(f"{INVENTORY_SERVICE_URL}/inventory/{item.product_id}/reserve")
httpx.ConnectTimeout: Connection timeout to inventory-service
Service: order-service
Endpoint: POST /orders
Status: 500 Internal Server Error
Timestamp: 2025-01-15T20:15:12.456Z
Error: Failed to reserve inventory - inventory-service timeout
```

