from dotenv import load_dotenv
import json
import os


load_dotenv()

USERS = json.loads(os.getenv("USERS"))
