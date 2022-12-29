# Rest API standards in this project

# Standard RESPONSE object. 
Most Rest API endpoints will return

```json
{
    "message": "Success!",
    "data": [
        {"key": "value"}
    ]
}
```

If there is an error

```json
{
    "message": "Failed!",
    "error": 1
}
```

Notice that data is replaced by the error property.
When response is successful, error property may or may not be sent (to avoid redundancy), therefore, front-end should check `data` or `error` properties
All responses should include a message, this can be shown in front-end or it can be used to customize another message.

Most of this is dealt with the `json_response` function.