# Lead Agent Runtime Config 规格变更

## ADDED Requirements

### Requirement: Hot reload Docker 后端必须暴露仓库根目录工具包

When the hot reload backend Docker image starts DeerFlow from `/app/backend`, the process SHALL include both `/app` and `/app/backend` on Python import path so configured repository-root business tools such as `tools.oceanengine_local_project` can be resolved.

#### Scenario: Hot reload backend resolves root tools package

- **GIVEN** the backend container is built from `docker/Dockerfile.backend.hot`
- **AND** the application files are available under `/app`
- **WHEN** the default CMD starts Gateway from `/app/backend`
- **THEN** `PYTHONPATH` SHALL include `/app`
- **AND** `PYTHONPATH` SHALL include `/app/backend`
- **AND** configured `tools.oceanengine_local_*` modules SHALL be importable without installing a third-party `tools` package

#### Scenario: Hot reload image is built without mounting the full repository

- **GIVEN** the backend container is built from `docker/Dockerfile.backend.hot`
- **WHEN** the image is created
- **THEN** the image SHALL copy repository-root `tools/` to `/app/tools`
- **AND** configured `tools.oceanengine_local_*` modules SHALL exist in the image filesystem
