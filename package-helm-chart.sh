#!/bin/env bash

set -xeuo pipefail

FULL_REF=$(git describe --tags)
VERSION="${FULL_REF#*@}"

# Check that alpha/beta versions have the form 2025.8.1+b1 requried by Helm
if [[ "${VERSION}" =~ '^[0-9]+\.[0-9]+\.[0-9]+(\+.*)?$' ]]; then
    echo "Valid version format: ${VERSION}"
else
    echo "Invalid version format: ${VERSION}. Expected format: X.Y.Z or X.Y.Z+string"
    return 1
fi

mkdir -p charts

cd helm

helm package -u --app-version ${VERSION} --version ${VERSION} .
mv *.tgz ../../charts
