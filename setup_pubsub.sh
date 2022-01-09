gcloud pubsub topics create $TOPIC_ID --project $PROJECT_ID

# Setup subscription with 10 minute message retention period (the minimum)
gcloud pubsub subscriptions create $SUBSCRIPTION_ID \
    --expiration-period 365d \
    --topic $TOPIC_ID \
    --project $PROJECT_ID \
    --message-retention-duration 10m
