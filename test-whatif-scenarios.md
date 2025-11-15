# Test What-If Scenarios for What-If Analyzer

## Scenario 1: Removing Email Functionality from Notification Service

```
I'm removing the notification-service email functionality. The service will no longer send emails, but other services still call it expecting email notifications.
```

---

## Scenario 2: Adding Credit Check to Payment Service

```
I'm adding a credit score check to the payment-service. The POST /payments endpoint will now make an HTTP call to credit-check-service before processing payments. This adds a new dependency and could slow down payment processing.
```

---

## Scenario 3: Changing User Service API

```
I'm modifying the user-service validation endpoint. The POST /users/{user_id}/validate endpoint is changing its response format from JSON to a simple boolean. This is a breaking change that will affect all services that call this endpoint.
```

---

## Scenario 4: Removing Kafka Topic

```
I'm removing the payment-events Kafka topic from payment-service. The service will no longer publish payment events, which means notification-service and other consumers won't receive payment notifications anymore.
```

---

## Scenario 5: Adding New Validation to Order Service

```
I'm adding inventory availability check to order-service. Before creating an order, it will now validate that all items are in stock by calling inventory-service. This adds a new dependency and could affect order creation performance.
```

---

## Scenario 6: Changing Product Service Endpoint

```
I'm deprecating the GET /products/{product_id} endpoint in product-service and replacing it with GET /products/v2/{product_id}. The new endpoint has a different response structure. All services calling the old endpoint need to be updated.
```

---

## Scenario 7: Adding Rate Limiting

```
I'm adding rate limiting to user-service. The service will now reject requests that exceed 100 requests per minute. This could cause failures in services that make frequent calls to user-service, like cart-service and order-service.
```

---

## Scenario 8: Changing Database Schema

```
I'm modifying the user database schema in user-service. The user table is being restructured, which will cause the GET /users/{user_id} endpoint to return different fields. Services like order-service and cart-service that depend on user data will be affected.
```

---

## Scenario 9: Removing Service Dependency

```
I'm removing the dependency on recommendation-service from cart-service. The cart-service will no longer fetch product recommendations, which means the recommendation-service will receive fewer requests.
```

---

## Scenario 10: Adding Authentication Requirement

```
I'm adding authentication requirement to all inventory-service endpoints. Previously public endpoints now require a valid JWT token. Services like order-service that call inventory-service will need to include authentication headers.
```

---

## Scenario 11: Changing Kafka Topic Name

```
I'm renaming the Kafka topic from "order-events" to "order-events-v2" in order-service. All services consuming "order-events" will stop receiving messages until they update to the new topic name.
```

---

## Scenario 12: Adding New Service Integration

```
I'm adding integration with a new shipping-service to order-service. After order creation, order-service will now call shipping-service to create shipping labels. This adds a new external dependency.
```

---

## Scenario 13: Performance Optimization Change

```
I'm optimizing the product-service by adding caching. The GET /products endpoint will now cache responses for 5 minutes. This could cause services to receive stale data if they expect real-time product information.
```

---

## Scenario 14: Removing Endpoint

```
I'm removing the POST /notifications/email endpoint from notification-service. Services like payment-service and order-service that send email notifications will fail when trying to call this endpoint.
```

---

## Scenario 15: Changing Response Format

```
I'm changing the response format of payment-service from JSON to XML. The POST /payments/process endpoint will now return XML instead of JSON. All services consuming this endpoint will break unless they update their parsing logic.
```

---

## Quick Copy-Paste Examples

### Simple Change (Notification Service):
```
I'm removing the notification-service email functionality. The service will no longer send emails, but other services still call it expecting email notifications.
```

### Adding Dependency (Payment Service):
```
I'm adding a credit score check to payment-service. The POST /payments endpoint will now call credit-check-service before processing payments.
```

### Breaking Change (User Service):
```
I'm modifying user-service validation endpoint. The POST /users/{user_id}/validate endpoint is changing its response format, which is a breaking change.
```

### Kafka Change:
```
I'm removing the payment-events Kafka topic from payment-service. Services consuming this topic will no longer receive payment notifications.
```

### API Change (Product Service):
```
I'm deprecating GET /products/{product_id} in product-service and replacing it with GET /products/v2/{product_id} with a different response structure.
```

