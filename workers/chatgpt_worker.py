import redis
import time
from openai import OpenAI
from typing import Iterator

redis_con = redis.Redis(host='localhost', port=6379, db=0)
openai_client = OpenAI()

def stream_chatgpt(prompt: str) -> Iterator[str]:
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
    item = redis_con.brpop("task_queue", timeout=0)[1]
    item = item.decode()
    print(f"Received: {item}")
    
    if item is not None:
        # messages are like "request_id:the message"
        request_id, message = item.split(":")
        response_queue = f"result-{request_id}"

        chunks = stream_chatgpt(message)
        for chunk in chunks:
            if chunk:
                redis_con.rpush(response_queue, chunk)

        # marker for end of message
        redis_con.rpush(response_queue, "DONEZO")


        # Put the item into the output queue
    else:
        print("item is unexpectedly none")
        break
