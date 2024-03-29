import logging
import os
from slack_bolt import App
import certifi
from .openai_handler import OpenAIHandler

# Set SSL certificate for secure requests
os.environ["SSL_CERT_FILE"] = certifi.where()


class SlackHandler:
    thread_messages = {}

    def __init__(
        self,
        allowed_users,
        bot_default_responses,
        SLACK_BOT_TOKEN,
        SIGNING_SECRET,
        OPENAI_API_KEY,
        DALLE_MODEL,
        CHATGPT_MODEL,
    ):
        self.openai = OpenAIHandler(
            OPENAI_API_KEY, DALLE_MODEL, CHATGPT_MODEL, bot_default_responses
        )
        self.app = App(signing_secret=SIGNING_SECRET, token=SLACK_BOT_TOKEN)
        self.allowed_users = allowed_users
        self.bot_default_responses = bot_default_responses

        # Direct Message Event
        @self.app.event("message")
        def handle_direct_messages(body):
            self.handle_event(body)

        # App Mention Event
        @self.app.event("app_mention")
        def handle_app_mentions(body):
            self.handle_event(body)

    def handle_message(self, msg, channel_id, thread_id):
        logging.info(
            "Authorized user - Msg received: %s in channel: %s and thread: %s",
            msg,
            channel_id,
            thread_id,
        )
        thread_history = self.thread_messages.get(thread_id, [])
        thread_history.append({"role": "user", "content": msg})

        response = self.app.client.chat_postMessage(
            channel=channel_id,
            text=":geppetto: ... :thought_balloon: ...",
            thread_ts=thread_id,
        )

        if response["ok"]:
            timestamp = response["message"]["ts"]
            logging.info("Timestamp of the posted message: %s", timestamp)
        else:
            logging.error("Failed to post the message.")

        response_from_chatgpt = self.openai.send_message(
            thread_history, self.send_preparing_image_message, channel_id, thread_id
        )
        if isinstance(response_from_chatgpt, str):
            thread_history.append(
                {"role": "assistant", "content": response_from_chatgpt}
            )
        self.thread_messages[thread_id] = thread_history

        try:
            if isinstance(response_from_chatgpt, bytes):
                self.app.client.files_upload_v2(
                    channel=channel_id,
                    thread_ts=thread_id,
                    username="Dall-E",
                    content=response_from_chatgpt,
                    title="Image",
                )
            else:
                logging.info("response from chatgpt: %s" % response_from_chatgpt)
                self.app.client.chat_update(
                    channel=channel_id,
                    text=response_from_chatgpt,
                    thread_ts=thread_id,
                    ts=timestamp,
                )
        except Exception as e:
            logging.error("Error posting message: %s", e)

    def send_preparing_image_message(self, channel_id, thread_id):
        dalle_message = self.bot_default_responses["dalle"]["preparing_image"]
        logging.info("Sending dalle default message: %s" % dalle_message)

        self.app.client.chat_postMessage(
            channel=channel_id,
            username="Dall-E",
            text=dalle_message,
            thread_ts=thread_id,
        )

    def handle_event(self, body):
        event = body["event"]
        msg = event["text"]
        channel_id = event["channel"]
        thread_id = event.get("thread_ts", None) or event["ts"]
        user_id = event.get("user")

        logging.info("Received event: %s" % event)
        logging.info("%s: %s" % (user_id, msg))

        # Check if user is allowed or * as wildcard to all users
        if "*" in self.allowed_users.values() or user_id in self.allowed_users.values():
            self.handle_message(msg, channel_id, thread_id)
        else:
            permission_denied_message = self.bot_default_responses["user"][
                "permission_denied"
            ]
            logging.info(
                "Sending permission denied default message: %s"
                % permission_denied_message
            )
            self.app.client.chat_postMessage(
                channel=channel_id,
                text=permission_denied_message,
                thread_ts=thread_id,
            )
