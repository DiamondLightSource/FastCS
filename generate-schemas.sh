#!/bin/env bash

set -euo pipefail

this_dir=$(dirname "$0")
cd "$this_dir"

helm schema -v || helm plugin install https://github.com/dadav/helm-schema

for chart in Charts/*; do
  helm schema -c $chart
  ln -fs ../$chart/values.schema.json schemas/$(basename $chart).schema.json
  # add a newline to the end of the schema file for pre-commit compliance
  echo >> schemas/$(basename $chart).schema.json
done
