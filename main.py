import os
from dotenv import load_dotenv

from core.boost_client import BoostChatClient, BoostClientConfig


def main():
    load_dotenv()
    print("Loaded BOOST_BASE_URL:", os.getenv("BOOST_BASE_URL"))

    base_url = os.environ["BOOST_BASE_URL"]
    api_key = os.getenv("BOOST_API_KEY") or None
    use_signature = (os.getenv("BOOST_USE_SIGNATURE", "false").lower() == "true")
    signing_secret = os.getenv("BOOST_SIGNING_SECRET") or None

    client = BoostChatClient(
        BoostClientConfig(
            base_url=base_url,
            api_key=api_key,
            use_signature=use_signature,
            signing_secret=signing_secret,
            timeout_s=30,
        )
    )

    convo, start_resp = client.start()
    print("START response:", start_resp)
    print("conversation_id:", convo.conversation_id)

    msg = "Hi! What credit card options do you have?"
    resp = client.post_text(convo, msg)
    print("\nPOST response:", resp)


if __name__ == "__main__":
    main()