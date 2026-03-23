#!/bin/bash

GITHUB_TOKEN="your_token_here"
OWNER="your_org_or_username"
REPO="your_repo_name"
WORKFLOW_ID="your_workflow_id"
PER_PAGE=100

delete_runs() {
  PAGE=1
  while :; do
    echo "📦 Fetching runs from page $PAGE..."
    RUNS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
      "https://api.github.com/repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/runs?per_page=$PER_PAGE&page=$PAGE" \
    | jq '.workflow_runs[]?.id')

    if [[ -z "$RUNS" ]]; then
      echo "✅ No more runs to delete. Done."
      break
    fi

    for RUN_ID in $RUNS; do
      echo "🗑️ Deleting run ID: $RUN_ID"
      curl -s -X DELETE \
        -H "Authorization: token $GITHUB_TOKEN" \
        "https://api.github.com/repos/$OWNER/$REPO/actions/runs/$RUN_ID"
    done

    ((PAGE++))
    sleep 1
  done
}

delete_runs