# Lead Agent Runtime Config 规格变更

## ADDED Requirements

### Requirement: 生产 Docker Gateway 必须暴露仓库根目录工具包

When the production Gateway container starts DeerFlow from `/app/backend`, the image and process SHALL include repository-root business tools so configured modules such as `tools.oceanengine_local_project` can be imported.

#### Scenario: Production Gateway image contains root tools package

- **GIVEN** the Gateway image is built from `backend/Dockerfile`
- **WHEN** the production runtime stage is assembled
- **THEN** the image SHALL copy repository-root `tools/` to `/app/tools`
- **AND** configured `tools.oceanengine_local_*` modules SHALL exist in the image filesystem

#### Scenario: Production Gateway process resolves root tools package

- **GIVEN** `docker/docker-compose.yaml` starts the production Gateway service
- **WHEN** Gateway starts from `/app/backend`
- **THEN** `PYTHONPATH` SHALL include `/app`
- **AND** `PYTHONPATH` SHALL include `/app/backend`
- **AND** configured `tools.oceanengine_local_*` modules SHALL be importable without installing a third-party `tools` package

#### Scenario: Production Gateway resolves OceanEngine project root

- **GIVEN** `docker/docker-compose.yaml` starts the production Gateway service
- **WHEN** OceanEngine native business tools resolve MCP configuration
- **THEN** the container SHALL expose `config.yaml` at `/app/config.yaml`
- **AND** the container SHALL expose skills at `/app/skills`
- **AND** `DEER_FLOW_PROJECT_ROOT` SHALL be set to `/app`
- **AND** OceanEngine MCP runtime SHALL be able to read project-root configuration from `/app`
