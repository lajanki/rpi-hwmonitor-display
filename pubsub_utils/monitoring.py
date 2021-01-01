import os
from google.cloud import monitoring_v3
from dotenv import load_dotenv


BASE = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(dotenv_path=os.path.join(BASE, ".env"))

PROJECT_ID = os.getenv("PROJECT_ID")
SUBSCRIPTION_ID = os.getenv("SUBSCRIPTION_ID")

client = monitoring_v3.MetricServiceClient()
result = monitoring_v3.query.Query(
    client,
    PROJECT_ID,
    "pubsub.googleapis.com/subscription/num_undelivered_messages",
    minutes=1).as_dataframe()