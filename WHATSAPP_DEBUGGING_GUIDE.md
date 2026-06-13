# WhatsApp Message Debugging Guide

## Overview
This guide helps debug WhatsApp message delivery issues in the unified conversation flow when users provide contact numbers.

## Common Issues & Solutions

### 1. Phone Number Format Issues

#### Symptoms
- Error: "Phone number is incorrect: Invalid phone number length"
- Error: "Phone number contains invalid characters"
- WhatsApp API returns 400 status code

#### Debugging Steps
1. Check the logs for phone number normalization:
   ```
   INFO: Phone number cleaning process
     original_input: "user_input_here"
     cleaned_input: "cleaned_version_here"
   ```

2. Look for validation errors:
   ```
   WARNING: Invalid contact number provided
     validation_error: "specific_error_here"
   ```

#### Solutions
- **Length Issues**: Ensure number has 10-15 digits
- **Invalid Characters**: Only numbers and + are allowed
- **Missing Country Code**: System automatically adds +91 for Indian numbers
- **Leading Zeros**: System automatically removes leading 0 and adds +91

### 2. WhatsApp API Authentication Issues

#### Symptoms
- HTTP 401 status code
- Error: "WhatsApp API authentication failed"

#### Debugging Steps
1. Check environment variables:
   ```bash
   # Verify these are set in .env
   META_ACCESS_TOKEN=your_token_here
   META_PHONE_NUMBER_ID=your_phone_id_here
   ```

2. Look for authentication logs:
   ```
   ERROR: WhatsApp API returned error status
     status_code: 401
     error_type: "authentication_failed"
   ```

#### Solutions
- Verify META_ACCESS_TOKEN is valid and not expired
- Check META_PHONE_NUMBER_ID is correct
- Ensure WhatsApp Business Account has proper permissions

### 3. Invalid Phone Number (Not Registered)

#### Symptoms
- HTTP 400 status code with "invalid phone number" message
- User reports message not received

#### Debugging Steps
1. Check WhatsApp API response:
   ```
   ERROR: WhatsApp API returned error status
     error_message: "Phone number not registered with WhatsApp"
   ```

2. Verify normalized phone number:
   ```
   INFO: Phone number successfully normalized
     normalized_number: "+919876543210"
   ```

#### Solutions
- Confirm the contact person has WhatsApp installed
- Verify the phone number is registered with WhatsApp
- Try sending to a known working WhatsApp number for testing

### 4. Rate Limiting Issues

#### Symptoms
- HTTP 429 status code
- Error: "WhatsApp API rate limit exceeded"

#### Debugging Steps
1. Look for rate limit logs:
   ```
   ERROR: WhatsApp API returned error status
     status_code: 429
     error_type: "rate_limit_exceeded"
   ```

#### Solutions
- Wait before retrying (usually 1 minute)
- Check if your WhatsApp Business Account has sufficient messaging limits
- Consider upgrading your WhatsApp Business API tier

### 5. Network/Connection Issues

#### Symptoms
- Error: "WhatsApp API request timed out"
- Error: "Unable to connect to WhatsApp API"

#### Debugging Steps
1. Check for network errors:
   ```
   ERROR: WhatsApp API connection error
     connection_error: "connection_details_here"
   ```

#### Solutions
- Verify internet connectivity
- Check if WhatsApp API endpoint is accessible
- Try again after a few moments

## How to Enable Enhanced Debugging

### 1. Set Logging Level
Update your logging configuration to capture all debug information:

```python
# In app/main.py or logging config
import logging
logging.getLogger("app.whatsapp_service").setLevel(logging.INFO)
logging.getLogger("app.support_flow").setLevel(logging.INFO)
```

### 2. Monitor Logs During Message Sending
Watch for these log entries in sequence:

```
INFO: Processing contact number input
INFO: Phone number cleaning process  
INFO: Phone number successfully normalized
INFO: Attempting to send WhatsApp message
INFO: WhatsApp API raw response
INFO: WhatsApp message sent successfully
```

If any step fails, the logs will show exactly where and why.

## Testing Phone Number Formats

### Valid Formats (Should Work)
- `9876543210` → Normalized to `+919876543210`
- `+919876543210` → Already correct
- `919876543210` → Normalized to `+919876543210`
- `09876543210` → Normalized to `+919876543210`
- `98765 43210` → Normalized to `+919876543210`

### Invalid Formats (Will Show Error)
- `123` → Too short
- `abcd123456` → Contains letters
- `123456789012345678` → Too long

## Manual Testing Steps

### 1. Test Phone Number Validation
1. Use the contact number flow
2. Try different phone number formats
3. Check logs for normalization process
4. Verify error messages are user-friendly

### 2. Test WhatsApp Message Sending
1. Use a known working WhatsApp number
2. Check if message is received
3. Verify message format and content
4. Check logs for successful delivery

### 3. Test Error Handling
1. Try invalid phone numbers
2. Try numbers not registered with WhatsApp
3. Verify users get helpful error messages
4. Ensure users can retry with corrected numbers

## Log Analysis Examples

### Successful Message Send
```
INFO: Processing contact number input - original_phone: +911234567890, contact_input: 9876543210
INFO: Phone number successfully normalized - normalized_number: +919876543210
INFO: WhatsApp message sent successfully - message_id: wamid.xxx, response: {...}
INFO: Breakdown alert successfully sent to contact person
```

### Failed Message Send
```
WARNING: Invalid contact number provided - validation_error: Invalid phone number length
ERROR: Failed to send breakdown alert to contact person - error: Invalid phone number format
```

## Quick Fixes

1. **Phone Format Issues**: Update phone number with country code
2. **API Issues**: Check .env file for correct tokens
3. **Network Issues**: Retry after a few seconds
4. **Rate Limits**: Wait 1 minute before retry
5. **Invalid Numbers**: Verify number is registered with WhatsApp