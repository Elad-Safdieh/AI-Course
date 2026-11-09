# intro_to_gcp — from a file in the cloud to a page in the browser

```
Browser  ──►  Cloud Run (main.py)  ──►  Cloud Storage: gs://<BUCKET>/message.txt  (private)
```

- `main.py` — Flask app. Reads `message.txt` from the bucket **on every request** and shows its name and content.
  Missing file, missing permission, non-UTF-8 file and missing config each get a clear message and a "retry" button.
- Config comes from env vars `BUCKET_NAME` and `OBJECT_NAME` (default `message.txt`). No keys in the code:
  on Cloud Run the app uses the service's own service account.

## Deploy (PowerShell)

Fill in the first three values; nothing here is a secret.

```powershell
$PROJECT = "<your-project-id>"
$REGION  = "me-west1"            # Tel Aviv; any Cloud Run region works
$BUCKET  = "<globally-unique-bucket-name>"
$SA      = "message-reader@$PROJECT.iam.gserviceaccount.com"

# 1. Point gcloud at the right project and enable the APIs
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com storage.googleapis.com

# 2. PRIVATE bucket + message.txt = "גרסה 1"
gcloud storage buckets create gs://$BUCKET --location=$REGION --uniform-bucket-level-access --public-access-prevention
[IO.File]::WriteAllText("$PWD\message.txt", "גרסה 1", (New-Object Text.UTF8Encoding $false))
gcloud storage cp message.txt gs://$BUCKET/message.txt
Remove-Item message.txt

# 3. Service identity with read-only access to THIS bucket only
gcloud iam service-accounts create message-reader --display-name "Cloud Run message reader"
gcloud storage buckets add-iam-policy-binding gs://$BUCKET --member "serviceAccount:$SA" --role roles/storage.objectViewer

# 4. Deploy from source (Cloud Build builds the container; no Docker needed locally)
#    Who may open the URL: --allow-unauthenticated = anyone with the link.
#    Use --no-allow-unauthenticated instead if project policy requires sign-in.
gcloud run deploy message-page --source . --region $REGION `
  --service-account $SA `
  --set-env-vars "BUCKET_NAME=$BUCKET,OBJECT_NAME=message.txt" `
  --allow-unauthenticated

# 5. URL + current revision (record it; it must stay the same after replacing the file)
gcloud run services describe message-page --region $REGION --format "value(status.url,status.latestReadyRevisionName)"
```

## Checks from the exercise

| Check | How |
|---|---|
| Shows `גרסה 1` | Open the URL |
| Live content | Console → bucket → upload `message.txt` with `גרסה 2` at the same path → refresh. Revision name from step 5 must not change. |
| Missing file | Rename the object in Console (e.g. `message.bak`) → refresh → "הקובץ לא נמצא" page (HTTP 404). Rename it back. |
| Bucket is private | `gcloud storage buckets describe gs://$BUCKET --format "value(public_access_prevention)"` → `enforced` |
