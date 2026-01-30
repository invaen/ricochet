"""Tests for SQLi OOB payload generator."""

import pytest

from ricochet.payloads.sqli import SQLiPayloadGenerator


class TestSQLiPayloadGenerator:
    """Test SQLiPayloadGenerator class."""

    def test_vuln_type_is_sqli(self):
        """Generator should have vuln_type 'sqli'."""
        gen = SQLiPayloadGenerator()
        assert gen.vuln_type == "sqli"

    def test_databases_constant(self):
        """Should have DATABASES list with all supported databases."""
        assert SQLiPayloadGenerator.DATABASES == [
            "mssql", "mysql", "oracle", "postgres"
        ]

    def test_generate_all_databases(self):
        """Should generate payloads for all databases when none specified."""
        gen = SQLiPayloadGenerator()
        payloads = list(gen.generate("test.callback.com"))

        # At least 2 payloads per database = 8 minimum
        assert len(payloads) >= 8

        # All 4 databases represented
        databases = {p[1] for p in payloads}
        assert databases == {"mssql", "mysql", "oracle", "postgres"}

    def test_generate_specific_database(self):
        """Should generate only specified database payloads."""
        gen = SQLiPayloadGenerator("mssql")
        payloads = list(gen.generate("test.callback.com"))

        # Only MSSQL payloads
        assert all(p[1] == "mssql" for p in payloads)
        assert len(payloads) >= 2

    def test_generate_each_database(self):
        """Each database should generate at least 2 payloads."""
        for db in SQLiPayloadGenerator.DATABASES:
            gen = SQLiPayloadGenerator(db)
            payloads = list(gen.generate("test.callback.com"))
            assert len(payloads) >= 2, f"{db} should have at least 2 payloads"

    def test_callback_substitution(self):
        """Callback URL should be substituted in payloads."""
        gen = SQLiPayloadGenerator()
        callback = "unique-callback-12345.example.com"
        payloads = list(gen.generate(callback))

        # All payloads should contain the callback
        for payload, db in payloads:
            assert callback in payload, f"Payload for {db} missing callback"
            # No leftover placeholder
            assert "{{CALLBACK}}" not in payload

    def test_invalid_database_raises(self):
        """Unknown database should raise ValueError."""
        with pytest.raises(ValueError) as exc:
            SQLiPayloadGenerator("mongodb")
        assert "Unknown database" in str(exc.value)
        assert "mongodb" in str(exc.value)

    def test_payloads_are_tuples(self):
        """Generate should yield (payload, database) tuples."""
        gen = SQLiPayloadGenerator()
        payloads = list(gen.generate("test.com"))

        for item in payloads:
            assert isinstance(item, tuple)
            assert len(item) == 2
            payload, db = item
            assert isinstance(payload, str)
            assert db in SQLiPayloadGenerator.DATABASES

    def test_mssql_payloads_contain_expected_techniques(self):
        """MSSQL payloads should use xp_dirtree or xp_fileexist."""
        gen = SQLiPayloadGenerator("mssql")
        payloads = [p[0] for p in gen.generate("test.com")]

        # At least one payload with each technique
        assert any("xp_dirtree" in p for p in payloads)

    def test_mysql_payloads_contain_expected_techniques(self):
        """MySQL payloads should use LOAD_FILE."""
        gen = SQLiPayloadGenerator("mysql")
        payloads = [p[0] for p in gen.generate("test.com")]

        assert any("LOAD_FILE" in p for p in payloads)

    def test_oracle_payloads_contain_expected_techniques(self):
        """Oracle payloads should use UTL_HTTP or UTL_INADDR."""
        gen = SQLiPayloadGenerator("oracle")
        payloads = [p[0] for p in gen.generate("test.com")]

        assert any("UTL_HTTP" in p or "UTL_INADDR" in p for p in payloads)

    def test_postgres_payloads_contain_expected_techniques(self):
        """PostgreSQL payloads should use dblink or COPY."""
        gen = SQLiPayloadGenerator("postgres")
        payloads = [p[0] for p in gen.generate("test.com")]

        assert any("dblink" in p or "COPY" in p for p in payloads)
