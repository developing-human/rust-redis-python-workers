This project provides an example of how to create a Rust websocket endpoint 
which streams responses from Python workers through Redis.

### System setup requires
1. A local Redis server running on the default port
2. `websocat` for a terminal based websocket client

### Setup & start a python worker
1. `cd workers/`
2. Create & activate a venv
3. `pip install -r requirements.txt`
4. `python3 chatgpt_worker.py`

### Setup & start the Rust API
1. `cd api`
2. `cargo run`

### Interact via websockets
1. `websocat --no-line ws://127.0.0.1:8080/ws`
2. type a prompt, press enter

### Expected result
1. The Rust server logging that it writes to the task queue
2. The Python worker picking up a task
3. Websocat writing the ChatGPT response as it comes back

https://github.com/developing-human/rust-redis-python-workers/assets/122365292/cf06470b-cdf1-4232-93f6-842fef488f0f

