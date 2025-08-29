# Charts

This directory contains Helm charts for deploying FastCS services.

TODO: The implementation of helm charts in this repo is intended to be general purpose and is a proposed solution for the `python-copier-template`.

## Github Actions

This folder works in tandem with [_helm.yml](../.github/workflows/_helm.yml) github actions workflow which:

- Validates the stricter form of SemVer tag that helm requires.
- Finds all subfolders in the `Charts` directory and packages them as Helm charts.
- Publishes the packaged charts to ghcr.io/${{github.repository_owner }}/charts/CHART_NAME
- Uploads the contents of /schemas to artifacts (meaning they will be published to the release)

This standalone Helm related workflow is independent of the rest of the workflows except that the _pypi workflow has _helm added to its `needs` in `ci.yml`, making sure we only publish to pypi with valid SemVer tags.

TODO: for a project that publishes containers referred to by the helm chart, the `_containers.yml` workflow should be added to the `needs` of _helm in `ci.yml`.

## Schema Generation

Schema generation for charts' `values.yaml` is handled by [helm-values-schema-json](https://github.com/losisin/helm-values-schema-json). Which is in turn controlled by annotations in the default [values.yaml](fastcs/values.yaml) file.

The generated schema file will be called `values.schema.json` and will be placed in the same directory as the `values.yaml` file and commited to the repo. This is done automatically by a [pre-commit hook](https://github.com/DiamondLightSource/FastCS/blob/8232393b38cc8e0eee00680e95c2ce06e7983ba6/.pre-commit-config.yaml#L27-L33). Therefore, when developing charts you can update schemas with:

```bash
git add . ; pre-commit
```

Note that this standard name for the schema file means that it is packaged up with the helm chart and available for schema checks in ArgoCD for example.

## schemas folder

The schemas folder allows us to declare the schemas you want to publish to the release.

It should contain:

- A symlink to each of the `values.schema.json` files in the subfolders of `Charts`. The symlink should have a unique name, e.g. `fastcs-values.schema.json`, thus allowing multiple schemas to be published per repo.
- A service schema file which references the above and can be used to validate `values.yaml` in epics-containers services repos, where the these charts will be used as sub-charts. e.g. [fastcs-service.schema.json](../schemas/fastcs-service.schema.json)

The service schema files are hand coded as they are extremely simple. The symlinks are also manually created at present. (both of these could potentially be automated).

## Debuging/Development In-Cluster

The `fastcs` helm chart has two variables to enable debugging/development in-cluster:

- `editable`: When true:
  - a PVC is created.
  - The debug version of the container image is referenced.
  - The contents of /workspaces and /venv are copied into the PVC.
  - The venv from the debug image is an editable install of the project source code in /workspaces.
  - The PVC folders are mounted over the corresponding folders in the container.
- `autostart`:
  - When false, the container starts with PID 1 as sleep infinity.
  - When true, the container starts with its normal entrypoint.

In combination these flags can be used to debug or develop in-cluster.

An initial demonstration script to use these features is provided in [debug.py](https://github.com/epics-containers/p47-services/blob/add-fastcs/debug.py) in the `p47-services` repo.

This script will:

- inspect the values of `editable` and `autostart` in the `values.yaml` file of the specified IOC (TODO: at present it uses the p47-services source code to do so but this should be determined from the cluster in future).
- port forward the debugpy port (5678) from the pod to localhost.
- If editable is true, it will mount the PVC locally using pv-mounter and open VSCode to the /workspaces/xxx folder.
- If autostart is false, it will exec into the container and launch debugpy to run the main program.
- If autostart is true, it will exec into the container and attach debugpy to PID 1.

This then allows you to attach VSCode to debugpy in the cluster container and if 'editable' is true, edit the source code in VSCode and have the changes reflected.

To attach to debugpy the following launch.json configuration is supplied in the [fastcs-example project](https://github.com/DiamondLightSource/fastcs-example/blob/77daed5f5a2bd01ab4c0e1d8c812e8754b254674/.vscode/launch.json#L7-L22). (this will also go in python-copier-template in future).
