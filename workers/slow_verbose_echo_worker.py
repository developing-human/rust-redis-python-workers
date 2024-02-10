import redis
import time

redis_con = redis.Redis(host='localhost', port=6379, db=0)

while True:
    item = redis_con.brpop("task_queue", timeout=0)[1]
    item = item.decode()
    print(item)
    
    if item is not None:
        # messages are like "request_id:the message"
        request_id, message = item.split(":")
        response_queue = f"result-{request_id}"

        verbose_response = f"You sent a message of {message}"
        words = verbose_response.split(' ')
        
        for i, word in enumerate(words):
            padded_word = " " + word if i > 0 else word
            redis_con.rpush(response_queue, padded_word)
            
            if i < len(words) - 1:
                time.sleep(1)

        # marker for end of message
        redis_con.rpush(response_queue, "DONEZO")

    else:
        print("item is unexpectedly none")
        break
