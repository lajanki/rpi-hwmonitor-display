gcloud pubsub topics create $TOPIC_ID --project $PROJECT_ID

# Setup subscription with 10 minute message retention period (the minimum)
gcloud pubsub subscriptions create $SUBSCRIPTION_ID \
    --expiration-period 365d \
    --topic $TOPIC_ID \
    --project $PROJECT_ID \
    --message-retention-duration 10m

# Create a service account with access to publish messages to the topic
gcloud iam service-accounts create hwmonitor \
    --description="hwmonitor worker identity" \
    --project $PROJECT_ID

gcloud pubsub topics add-iam-policy-binding $TOPIC_ID \
    --member="serviceAccount:hwmonitor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher" \
    --project $PROJECT_ID

gcloud pubsub subscriptions add-iam-policy-binding $SUBSCRIPTION_ID \
    --member="serviceAccount:hwmonitor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.subscriber" \
    --project $PROJECT_ID
