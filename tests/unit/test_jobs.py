"""Unit tests for Dagster job definitions."""

from dagster_pipelines.jobs import venom_flow_pipeline


class TestVenomFlowPipeline:
    """Test pipeline job definition."""

    def test_job_exists(self):
        assert venom_flow_pipeline is not None

    def test_job_name(self):
        assert venom_flow_pipeline.name == "venom_flow_pipeline"

    def test_job_has_description(self):
        assert venom_flow_pipeline.description is not None
        assert len(venom_flow_pipeline.description) > 0
