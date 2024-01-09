import logging
import os
from slack_bolt import App
from slack_sdk import WebClient
import certifi
from srcs.openai_handler import OpenAIHandler

# Set SSL certificate for secure requests
os.environ["SSL_CERT_FILE"] = certifi.where()

# Define global variables
thread_messages = {}


# TODO: maybe use a separate config file with all the dictionaries/descriptions


class SlackHandler:
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
        self.openai_scripts = OpenAIHandler(OPENAI_API_KEY, DALLE_MODEL, CHATGPT_MODEL)

        # Initialize Slack client
        self.client = WebClient(token=SLACK_BOT_TOKEN)

        # Define Slack app
        self.app = App(signing_secret=SIGNING_SECRET, token=SLACK_BOT_TOKEN)

        # Initialize instances for handling messages and mentions
        self.slack_methods = SlackMethods(
            self.app,
            self.client,
            allowed_users,
            bot_default_responses,
            self.openai_scripts,
        )

        # Direct Message Event
        @self.app.event("message")
        def handle_direct_messages(body):
            self.slack_methods.handle_event(body)

        # App Mention Event
        @self.app.event("app_mention")
        def handle_app_mentions(body):
            self.slack_methods.handle_event(body)


class SlackMethods:
    def __init__(
        self,
        app: App,
        client: WebClient,
        allowed_users,
        bot_default_responses,
        openai_scripts: OpenAIHandler,
    ):
        self.app = app
        self.client = client
        self.allowed_users = allowed_users
        self.bot_default_responses = bot_default_responses
        self.openai_scripts = openai_scripts

    def handle_event(self, body):
        event = body["event"]
        msg = event["text"]
        channel_id = event["channel"]
        thread_id = event.get("thread_ts", None) or event["ts"]
        user_id = event.get("user")

        # TODO: add logging information about the current event
        logging.info("Received event: %s" % event)
        logging.info("%s: %s" % (user_id, msg))

        # Check if user is allowed
        if self.is_allowed(user_id):
            if "hola" in msg.lower():
                self.handle_greeting_spanish(channel_id, thread_id)
            elif "hello" in msg.lower():
                self.handle_greeting_english(channel_id, thread_id)
            elif "dalle" in msg.lower():
                self.handle_dalle(msg, channel_id, thread_id)
            elif msg:
                self.handle_default(msg, channel_id, thread_id)
        else:
            self.send_permission_denied(channel_id, thread_id)

    def is_allowed(self, user_id):
        """Check if a user is allowed to interact with the bot."""
        return user_id in self.allowed_users.values()

    def handle_greeting_spanish(self, channel_id, thread_id):
        image_path = os.path.join("assets", "GeppettoMini.png")

        greeting_message = self.bot_default_responses["greetings"]["spanish"]
        logging.info("Sending greeting message with file upload: %s" % greeting_message)

        self.client.files_upload(
            channels=channel_id,
            initial_comment=greeting_message,
            file=image_path,
            thread_ts=thread_id,
            filetype="png",
        )

        features_message = self.bot_default_responses["features"]["spanish"]
        logging.info("Sending features message: %s" % features_message)

        self.app.client.chat_postMessage(
            channel=channel_id,
            text=features_message,
            thread_ts=thread_id,
        )

    def handle_greeting_english(self, channel_id, thread_id):
        image_path = os.path.join("assets", "GeppettoMini.png")

        greeting_message = self.bot_default_responses["greetings"]["english"]
        logging.info("Sending greeting message with file upload: %s" % greeting_message)

        self.client.files_upload(
            channels=channel_id,
            initial_comment=greeting_message,
            file=image_path,
            thread_ts=thread_id,
            filetype="png",
        )

        features_message = self.bot_default_responses["features"]["english"]
        logging.info("Sending features message: %s" % features_message)

        self.app.client.chat_postMessage(
            channel=channel_id, text=features_message, thread_ts=thread_id
        )

    def handle_dalle(self, msg, channel_id, thread_id):
        _, prompt = self.thread_prompt(msg, thread_id)

        logging.info("prompt: %s" % (prompt))

        dalle_message = self.bot_default_responses["dalle"]["preparing_image"]
        logging.info("Sending dalle default message: %s" % dalle_message)

        self.client.chat_postMessage(
            channel=channel_id,
            username="Dall-E",
            text=dalle_message,
            thread_ts=thread_id,
        )

        url = self.openai_scripts.text_to_image_url(prompt=prompt)
        self.openai_scripts.url_to_image(url=url)
        # TODO: if image is returned, we could use it in the response
        self.client.files_upload(
            channels=channel_id,
            thread_ts=thread_id,
            username="Dall-E",
            file=os.path.join("assets", "dall-e.png"),
            title="respuesta",
        )

    def handle_default(self, msg, channel_id, thread_id):
        thread_history, prompt = self.thread_prompt(msg, thread_id)

        response = self.app.client.chat_postMessage(
            channel=channel_id,
            text=":geppetto: ... :thought_balloon: ...",
            thread_ts=thread_id,
        )

        if response["ok"]:
            timestamp = response["message"]["ts"]
            # TODO: use logger here
            logging.info(f"Timestamp of the posted message: {timestamp}")
        else:
            logging.error("Failed to post the message.")

        response_from_chatgpt = self.openai_scripts.generate_chatgpt_response(prompt)
        logging.info("response from chatgpt: %s" % response_from_chatgpt)

        thread_history.append({"content": response_from_chatgpt})
        thread_messages[thread_id] = thread_history

        try:
            self.app.client.chat_update(
                channel=channel_id,
                text=response_from_chatgpt,
                thread_ts=thread_id,
                ts=timestamp,
            )
        except Exception as e:
            # TODO: use logger here
            logging.info(f"Error posting message: {e}")

    def send_permission_denied(self, channel_id, thread_id):
        permission_denied_message = self.bot_default_responses["user"][
            "permission_denied"
        ]
        logging.info(
            "Sending permission denied default message: %s" % permission_denied_message
        )

        self.app.client.chat_postMessage(
            channel=channel_id,
            text=permission_denied_message,
            thread_ts=thread_id,
        )

    def thread_prompt(self, msg, thread_id):
        thread_history = thread_messages.get(thread_id, [])
        thread_history.append({"role": "user", "content": msg})
        thread_messages[thread_id] = thread_history
        prompt = "\n".join([m["content"] for m in thread_history])
        return thread_history, prompt
