#!/bin/bash
# Hook: on_feature_done — print a summary of the completed feature
echo "Feature completed: ${FEATURE_ID:-?} — ${FEATURE_NAME:-?}"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Agent: ${AGENT_NAME:-unknown}"
exit 0
