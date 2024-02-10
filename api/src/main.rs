use actix::{Actor, AsyncContext, Handler, Message, StreamHandler, WrapFuture};
use actix_web::{web::{self, Data}, App, Error, HttpRequest, HttpResponse, HttpServer};
use actix_web_actors::ws::{self};
use redis::{self, AsyncCommands, Client};
use uuid::Uuid;

struct WebSocketActor {
    // Client is passed to the Actor because it can be cloned, unlike connection
    redis_client: web::Data<Client>
}

impl Actor for WebSocketActor {
    type Context = ws::WebsocketContext<Self>;
}


#[derive(Message)]
#[rtype(result = "()")]
struct TextMessage(String);

impl Handler<TextMessage> for WebSocketActor {
    type Result = ();

    fn handle(&mut self, msg: TextMessage, ctx: &mut Self::Context) {
        ctx.text(msg.0);
    }
}

impl StreamHandler<Result<ws::Message, ws::ProtocolError>> for WebSocketActor {
    fn handle(&mut self, msg: Result<ws::Message, ws::ProtocolError>, ctx: &mut Self::Context) {
        if let Ok(ws::Message::Text(text)) = msg {
            if text.len() == 1 {
                return  // Ignore newline-only (i.e. adding blank line in websocat)
            }

            let addr = ctx.address();
            let client = self.redis_client.clone();

            // redis communication needs to happen inside an async block for the
            // websocket to be able to communicate as it's written to
            let fut = async move {
                let mut con = client.get_async_connection().await.unwrap();

                let request_id = Uuid::new_v4().to_string();
                let message = format!("{request_id}:{}", text.trim());

                // Write the message to the task queue for a python worker to pickup
                let _: () = con.lpush("task_queue", &message).await.unwrap();
                println!("Wrote '{message}' to task_queue");
                
                // Read the response from the response queue until DONEZO is received
                // Print the name of the queue to test with redis-cli
                let result_queue = format!("result-{request_id}");
                println!("Reading results from: {result_queue}");

                let mut result_part: (String, String) = con.brpop(&result_queue, 0.0).await.unwrap();
                while result_part.1 != "DONEZO" {
                    // Send this part of the response to the websocket client
                    addr.do_send(TextMessage(result_part.1));
                    
                    // Get the next part of the response
                    result_part = con.brpop(&result_queue, 0.0).await.unwrap();
                }

                addr.do_send(TextMessage("\n".to_string()));
            };

            ctx.spawn(fut.into_actor(self));
        }
    }
}



async fn index(
    req: HttpRequest,
    stream: web::Payload,
    redis_client: web::Data<redis::Client>,
) -> Result<HttpResponse, Error> {
    // Defer to WebSocketActor.handle() whenever a message comes in
     ws::start(WebSocketActor {redis_client}, &req, stream)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let client = redis::Client::open("redis://127.0.0.1").unwrap();
    let client = Data::new(client);
    HttpServer::new(move || {
        App::new()
            .app_data(Data::clone(&client))
            .route("/ws/", web::get().to(index))
    })
    .bind(("127.0.0.1", 8080))?
    .run()
    .await
}
