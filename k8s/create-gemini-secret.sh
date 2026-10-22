#!/usr/bin/env bash
# Prompt for a Gemini key and send it directly to Kubernetes without a key file.
set +x
set -euo pipefail

if [[ $# -ne 0 ]]; then
    printf 'Usage: bash k8s/create-gemini-secret.sh (no arguments)\n' >&2
    exit 1
fi

command -v kubectl >/dev/null || {
    printf 'kubectl must be installed and configured first.\n' >&2
    exit 1
}

# Use the current context, as configured during the S3DF setup instructions.
printf 'Kubernetes context: '
kubectl config current-context
printf 'Creating Secret spine-learn-gemini in namespace spine-learn.\n'

# Disable echo while reading; never place the credential in command arguments.
trap 'unset gemini_key' EXIT
IFS= read -r -s -p 'Gemini API key: ' gemini_key
printf '\n'
if [[ -z "$gemini_key" ]]; then
    printf 'The API key cannot be empty.\n' >&2
    exit 1
fi

# Creation fails if the Secret already exists, leaving the existing key intact.
printf '%s' "$gemini_key" |
    kubectl -n spine-learn create secret generic spine-learn-gemini \
        --from-file=api-key=/dev/stdin
