import os
# run: export TELEGRAM_BOT_TOKEN="YOUR_TOKEN"
def load_config():
    """Load config from env variables or file"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        raise ValueError("Telegram token not found in environment variables")
    
    return {'telegram_bot_token': token}

config = load_config()
TOKEN = config['telegram_bot_token']
