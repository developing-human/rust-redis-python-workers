import redis
import time
from openai import OpenAI
from typing import Iterator

redis_con = redis.Redis(host='localhost', port=6379, db=0)
openai_client = OpenAI() # assumes OPENAI_API_KEY is available

def stream_chatgpt(prompt: str) -> Iterator[str]:
    """Sends the prompt to chat gpt, returns an iterator
    of the chunks/deltas returned by the streaming api"""

    response_stream = openai_client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[
        {"role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
        {"role": "user", "content": prompt}
      ],
      stream=True
    )
    
    for response in response_stream:
        yield response.choices[0].delta.content or ""

while True:
    # block until a task is available on the task_queue
    item = redis_con.brpop("task_queue", timeout=0)[1]
    if item is None:
        print("item is unexpectedly none")
        break

    item = item.decode()
    print(f"Received: {item}")
    
    # messages are like "request_id:the message"
    request_id, message = item.split(":", 1)
    response_queue = f"result-{request_id}"

    # push individual chunks onto the response queue
    chunks = stream_chatgpt(message)
    for chunk in chunks:
        if chunk:
            redis_con.rpush(response_queue, chunk)

    # marker for end of message
    redis_con.rpush(response_queue, "DONEZO")
