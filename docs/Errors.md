## Binbot Error codes

I've redesigned Binbot RESTful API error codes for 400 bad requests. Because we need more granular errors raised, since the default 422 by FastAPI is not enough here is the structure.

We extend 4XX errors instead of starting our own numbering system to make it easier to identify which group it belongs to followed by the error message.

Say we get bot POST request that returns an error of Bad Request, specifically a 422 (unprocessable entity), this still lacks specificity. In this case, let's say it's an error in the submission of a strategy field, not being part of the enums LONG/SHORT. In that case, we'd want to:
1. Throw a 422
2. Return an error code 4221
3. Return an informative message for the client "Strategy field must be LONG/SHORT", where error message most of the time would be raised in a Pydantic Model that raises an exception

So the BinbotError args would be
```
try:
    post_bot_function()
except BinbotErrors as error:
    BinbotErrors(
        code=4221,
        message=error.message
    )

```
