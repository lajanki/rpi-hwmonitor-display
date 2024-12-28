# Update PROJECT_ID to match your project!
PROJECT_ID="my-project"
TOPIC_ID="hwmonitor"

$SUBSCRIPTION_ID="${TOPIC_ID}-sub"


# Create a topic
gcloud pubsub topics create $TOPIC_ID --project $PROJECT_ID

# Setup subscription with minimal message retention
gcloud pubsub subscriptions create $SUBSCRIPTION_ID \
    --expiration-period 365d \
    --topic $TOPIC_ID \
    --project $PROJECT_ID \
    --message-retention-duration 10m

# Create a service account with access to publish messages to the topic
gcloud iam service-accounts create hwmonitor \
    --description "hwmonitor worker identity" \
    --project $PROJECT_ID

gcloud pubsub topics add-iam-policy-binding $TOPIC_ID \
    --member "serviceAccount:hwmonitor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role "roles/pubsub.publisher" \
    --project $PROJECT_ID

gcloud pubsub subscriptions add-iam-policy-binding $SUBSCRIPTION_ID \
    --member "serviceAccount:hwmonitor@$PROJECT_ID.iam.gserviceaccount.com" \
    --role "roles/pubsub.subscriber" \
    --project $PROJECT_ID

# Download a local json key
gcloud iam service-accounts keys create $HOME/Downloads/hwmonitor.json \
    --iam-account "hwmonitor@$PROJECT_ID.iam.gserviceaccount.com"

# point GOOGLE_APPLICATION_CREDENTIALS env variable to the key
echo "GOOGLE_APPLICATION_CREDENTIALS=$HOME/Downloads/hwmonitor.json" > .env