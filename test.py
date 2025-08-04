#!/usr/bin/env python3
"""
Test script to demonstrate standardized logging and backoff mechanisms
"""

import time
from utils import SlackLogger, SlackRateLimiter

def test_logging():
    """Test the standardized logging format."""
    logger = SlackLogger("TestTool")
    
    # Test phase logging
    logger.phase(1, "Starting test operations")
    
    # Test different log levels
    logger.info("This is an info message")
    logger.info("This is an indented info message", indent=1)
    logger.success("This is a success message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test API call logging
    logger.api_call("test.api", page=1, result_count=25)
    
    # Test progress logging
    total_items = 100
    for i in range(0, total_items + 1, 10):
        logger.progress(i, total_items, f"Processing item {i}")
        time.sleep(0.1)  # Simulate work
    
    # Test completion summary
    logger.completion_summary(total_items, 5.0)

def test_rate_limiter():
    """Test the standardized rate limiter."""
    logger = SlackLogger("RateLimitTest")
    rate_limiter = SlackRateLimiter(logger)
    
    logger.phase(2, "Testing rate limiting")
    
    # Test exponential backoff
    for attempt in range(3):
        logger.info(f"Simulating retry attempt {attempt + 1}")
        rate_limiter.exponential_backoff(attempt, max_wait=5.0)
    
    logger.success("Rate limiting test complete")

if __name__ == "__main__":
    print("🧪 Testing Standardized Slack Export Utilities\n")
    
    test_logging()
    test_rate_limiter()
    
    print("\n✅ All tests completed!")
