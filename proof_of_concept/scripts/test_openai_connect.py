# test_openai_connect.py
from openai import OpenAI

try:
    client = OpenAI()
    # Easiest lightweight call that proves auth + network
    models = client.models.list()
    print("OK ✅ Models count:", len(models.data))
except Exception as e:
    print("FAIL ❌", repr(e))
