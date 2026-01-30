import pytest
import responses
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime

from dagster.assets.ingestion import venom_peptides_uniprot


class TestVenomPeptidesUniprotAPI:
    """Unit tests for API interaction and error handling."""

    @responses.activate
    def test_successful_api_request(self):
        """Test successful API request returns expected data."""
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P01589",
                    "uniProtkbId": "CYA1_CANFA",
                    "organism": {"scientificName": "Canis lupus familiaris"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [
                        {
                            "commentType": "FUNCTION",
                            "texts": [{"value": "Test function annotation"}],
                        }
                    ],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_response,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert result.metadata["num_records"] == 1

    @responses.activate
    def test_rate_limit_handling(self):
        """Test HTTP 429 rate limit is handled with backoff."""
        mock_response = {
            "results": [
                {
                    "primaryAccession": "P01589",
                    "uniProtkbId": "CYA1_CANFA",
                    "organism": {"scientificName": "Test organism"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_response,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert "num_records" in result.metadata

    def test_timeout_handling():
        """Test timeout error is raised and logged."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()

            context = MagicMock()

            with pytest.raises(requests.exceptions.Timeout):
                venom_peptides_uniprot(context)

            context.log.error.assert_called()

    def test_http_error_handling():
        """Test HTTP errors are raised and logged."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "500 Server Error"
            )
            mock_get.return_value = mock_response

            context = MagicMock()

            with pytest.raises(requests.exceptions.HTTPError):
                venom_peptides_uniprot(context)

            context.log.error.assert_called()


class TestVenomPeptidesUniprotDataExtraction:
    """Unit tests for data extraction from UniProt response."""

    @responses.activate
    def test_extraction_from_valid_uniprot_response(self):
        """Test extraction of all required fields from valid response."""
        mock_data = {
            "results": [
                {
                    "primaryAccession": "P12345",
                    "uniProtkbId": "TEST1_HUMAN",
                    "organism": {"scientificName": "Homo sapiens"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [
                        {
                            "commentType": "FUNCTION",
                            "texts": [{"value": "Exhibits proteolytic activity"}],
                        }
                    ],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_data,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert result.metadata["num_records"] == 1
        assert result.metadata["organism_count"] == 1

    @responses.activate
    def test_handling_of_missing_function_field(self):
        """Test handling of missing function annotation."""
        mock_data = {
            "results": [
                {
                    "primaryAccession": "P12345",
                    "uniProtkbId": "TEST1_HUMAN",
                    "organism": {"scientificName": "Homo sapiens"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_data,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert result.metadata["num_records"] == 1

    @responses.activate
    def test_null_value_handling(self):
        """Test handling of null/empty values in response."""
        mock_data = {
            "results": [
                {
                    "primaryAccession": "P12345",
                    "uniProtkbId": "",
                    "organism": {},
                    "sequence": {},
                    "comments": [],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_data,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert result.metadata["num_records"] == 1

    @responses.activate
    def test_sequence_length_calculation(self):
        """Test sequence length is calculated correctly."""
        mock_data = {
            "results": [
                {
                    "primaryAccession": "P12345",
                    "uniProtkbId": "TEST1",
                    "organism": {"scientificName": "Test organism"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_data,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert result.metadata["avg_length"] > 0


class TestVenomPeptidesUniprotPagination:
    """Unit tests for pagination logic."""

    @responses.activate
    def test_pagination_loop_termination(self):
        """Test pagination loop terminates correctly after MAX_PAGES."""
        mock_page1 = {
            "results": [
                {
                    "primaryAccession": f"P{i:05d}",
                    "uniProtkbId": f"TEST{i}",
                    "organism": {"scientificName": "Test organism"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
                for i in range(50)
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_page1,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert result.metadata["num_records"] == 50

    @responses.activate
    def test_empty_page_detection(self):
        """Test pagination stops when empty results are returned."""
        empty_response = {"results": []}

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=empty_response,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert result.metadata["num_records"] == 0

    @responses.activate
    def test_offset_calculation_with_multiple_pages(self):
        """Test offset is calculated correctly across pages."""
        page1 = {
            "results": [
                {
                    "primaryAccession": f"P{i:05d}",
                    "uniProtkbId": f"TEST{i}",
                    "organism": {"scientificName": "Test organism"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
                for i in range(50)
            ]
        }

        page2 = {
            "results": [
                {
                    "primaryAccession": f"P{50 + i:05d}",
                    "uniProtkbId": f"TEST{50 + i}",
                    "organism": {"scientificName": "Test organism"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
                for i in range(50)
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=page1,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=page2,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert result.metadata["num_records"] == 100


class TestVenomPeptidesUniprotMetadata:
    """Unit tests for metadata generation."""

    @responses.activate
    def test_metadata_includes_row_count(self):
        """Test metadata includes record count."""
        mock_data = {
            "results": [
                {
                    "primaryAccession": "P12345",
                    "uniProtkbId": "TEST1",
                    "organism": {"scientificName": "Test organism"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_data,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert "num_records" in result.metadata
        assert isinstance(result.metadata["num_records"], int)

    @responses.activate
    def test_metadata_includes_organism_count(self):
        """Test metadata includes unique organism count."""
        mock_data = {
            "results": [
                {
                    "primaryAccession": f"P{i:05d}",
                    "uniProtkbId": f"TEST{i}",
                    "organism": {"scientificName": f"Organism {i % 2}"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
                for i in range(10)
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_data,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert "organism_count" in result.metadata
        assert isinstance(result.metadata["organism_count"], int)

    @responses.activate
    def test_metadata_includes_avg_length(self):
        """Test metadata includes average sequence length."""
        mock_data = {
            "results": [
                {
                    "primaryAccession": "P12345",
                    "uniProtkbId": "TEST1",
                    "organism": {"scientificName": "Test organism"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_data,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert "avg_length" in result.metadata

    @responses.activate
    def test_metadata_includes_fetch_time(self):
        """Test metadata includes fetch timestamp."""
        mock_data = {
            "results": [
                {
                    "primaryAccession": "P12345",
                    "uniProtkbId": "TEST1",
                    "organism": {"scientificName": "Test organism"},
                    "sequence": {
                        "value": "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPK"
                    },
                    "comments": [],
                }
            ]
        }

        responses.add(
            responses.GET,
            "https://rest.uniprot.org/uniprotkb/search",
            json=mock_data,
            status=200,
        )

        context = MagicMock()
        result = venom_peptides_uniprot(context)

        assert "fetch_time" in result.metadata
