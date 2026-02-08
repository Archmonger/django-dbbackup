"""Tests for custom metadata."""

import importlib

import pytest
from django.test import TestCase, override_settings

import dbbackup.settings
import dbbackup.utils

# Helpers
TEST_VAL = "aabbcc-1122-3344_eu-west"


def dummy_setter(metadata):
    return {"CSMT_VAL": TEST_VAL}


def broken_setter(metadata):
    return ["not", "a", "dict"]


def setter_returning_none(metadata):
    return None


def mutation_setter(context):
    context["mutated"] = True
    return {}


def mutation_validator(metadata):
    metadata["mutated"] = True
    return True


class CSTM:
    abc = "123"


def anotherbroken_setter(metadata):
    return {"CSMT_VAL": TEST_VAL, "CSTM_OBJ": CSTM()}


def dummy_validator(metadata):
    """Dummy validator for testing purposes that assues we only allow one type of customer and region.

    A real validator would probably do more complex checks.
    """
    if metadata.get("NO-OP", False):
        return None
    if val := metadata.get("CSMT_VAL", ""):
        if not val.startswith("aabbcc"):
            raise ValueError("CSMT_VAL must start with 'aabbcc'")
        if not val.endswith("eu-west"):
            return False
    return True


def broken_validator(metadata):
    print(1 / 0)  # Always raises ZeroDivisionError
    return True

def non_bool_validator(metadata):
    return "not a boolean"

DEFAULT_META = {'ENGINE': 'django.db.backends.sqlite3'}

# Actual tests
class CustomMetadataTest(TestCase):
    @override_settings(DBBACKUP_BACKUP_METADATA_SETTER="tests.test_user_metadata.dummy_setter")
    def test_metadata_setter_valid(self):
        """Test that setting DBBACKUP_BACKUP_METADATA_SETTER works."""
        importlib.reload(dbbackup.settings)

        assert dbbackup.settings.BACKUP_METADATA_SETTER == "tests.test_user_metadata.dummy_setter"
        assert dbbackup.utils.get_user_metadata(DEFAULT_META) == {"CSMT_VAL": TEST_VAL}

    @override_settings(DBBACKUP_BACKUP_METADATA_SETTER=dummy_setter)
    def test_metadata_setter_valid_callable(self):
        """Test that setting DBBACKUP_BACKUP_METADATA_SETTER works with a callable."""
        importlib.reload(dbbackup.settings)

        assert dbbackup.settings.BACKUP_METADATA_SETTER == dummy_setter
        assert dbbackup.utils.get_user_metadata(DEFAULT_META) == {"CSMT_VAL": TEST_VAL}

    @override_settings(DBBACKUP_BACKUP_METADATA_SETTER="tests.test_user_metadata.setter_returning_none")
    def test_metadata_setter_none(self):
        """Test that setting DBBACKUP_BACKUP_METADATA_SETTER works when returning None."""
        importlib.reload(dbbackup.settings)

        assert dbbackup.utils.get_user_metadata(DEFAULT_META) == {}

    @override_settings(DBBACKUP_BACKUP_METADATA_SETTER="tests.test_user_metadata.mutation_setter")
    def test_metadata_setter_no_side_effects(self):
        """Test that the setter cannot mutate the original context."""
        importlib.reload(dbbackup.settings)
        context = {"original": True}
        dbbackup.utils.get_user_metadata(context)
        assert context == {"original": True}
        assert "mutated" not in context

    @override_settings(DBBACKUP_BACKUP_METADATA_SETTER="non.existent.loader")
    def test_metadata_setter_invalid_1(self):
        """Test that various setter missconfigurations do not work - Non-existent module."""
        importlib.reload(dbbackup.settings)

        with pytest.raises(ImportError, match="Could not import module 'non.existent': No module named 'non'"):
            dbbackup.utils.get_user_metadata(DEFAULT_META)

    @override_settings(DBBACKUP_BACKUP_METADATA_SETTER="tests.test_user_metadata.TEST_VAL")
    def test_metadata_setter_invalid_2(self):
        """Test that various setter missconfigurations do not work - Non-callable object."""
        importlib.reload(dbbackup.settings)

        with pytest.raises(TypeError, match="The object at 'tests.test_user_metadata.TEST_VAL' is not callable."):
            dbbackup.utils.get_user_metadata(DEFAULT_META)

    @override_settings(DBBACKUP_BACKUP_METADATA_SETTER="tests.test_user_metadata.broken_setter")
    def test_metadata_setter_invalid_3(self):
        """Test that various setter missconfigurations do not work - Wrong return type."""
        importlib.reload(dbbackup.settings)

        with pytest.raises(ValueError, match="DBBACKUP_BACKUP_METADATA_SETTER must return a dictionary."):
            dbbackup.utils.get_user_metadata(DEFAULT_META)

    @override_settings(DBBACKUP_BACKUP_METADATA_SETTER="tests.test_user_metadata.anotherbroken_setter")
    def test_metadata_setter_invalid_4(self):
        """Test that various setter missconfigurations do not work - Not JSON serializable."""
        importlib.reload(dbbackup.settings)

        with pytest.raises(ValueError, match="Custom metadata is not JSON serializable"):
            dbbackup.utils.get_user_metadata(DEFAULT_META)

    @override_settings(DBBACKUP_RESTORE_METADATA_VALIDATOR="tests.test_user_metadata.dummy_validator")
    def test_metadata_validator_valid(self):
        """Test that setting DBBACKUP_RESTORE_METADATA_VALIDATOR works."""
        importlib.reload(dbbackup.settings)

        assert dbbackup.settings.RESTORE_METADATA_VALIDATOR == "tests.test_user_metadata.dummy_validator"
        assert dbbackup.utils.validate_user_metadata({"CSMT_VAL": TEST_VAL}) is True

        # Test that a validator can raise an exception
        with pytest.raises(ValueError, match="CSMT_VAL must start with 'aabbcc'"):
            dbbackup.utils.validate_user_metadata({"CSMT_VAL": "123"})

        # Test that a wrong also raises a ValueError
        assert dbbackup.utils.validate_user_metadata({"CSMT_VAL": "aabbcc-xyz_eu-central"}) is False

        # Test that no-op works
        assert dbbackup.utils.validate_user_metadata({"NO-OP": True}) is None

    @override_settings(DBBACKUP_RESTORE_METADATA_VALIDATOR="tests.test_user_metadata.mutation_validator")
    def test_metadata_validator_no_side_effects(self):
        """Test that the validator cannot mutate the original metadata."""
        importlib.reload(dbbackup.settings)
        metadata = {"original": True}
        assert dbbackup.utils.validate_user_metadata(metadata) is True
        assert metadata == {"original": True}
        assert "mutated" not in metadata

    @override_settings(DBBACKUP_RESTORE_METADATA_VALIDATOR="non.existent.validator")
    def test_metadata_validator_invalid_1(self):
        """Test that various validator missconfigurations do not work - Non-existent module."""
        importlib.reload(dbbackup.settings)

        with pytest.raises(ImportError, match="Could not import module 'non.existent': No module named 'non'"):
            dbbackup.utils.validate_user_metadata({"CSMT_VAL": TEST_VAL})

    @override_settings(DBBACKUP_RESTORE_METADATA_VALIDATOR="tests.test_user_metadata.broken_validator")
    def test_metadata_validator_invalid_2(self):
        """Test that various validator missconfigurations do not work - Exception during validation."""
        importlib.reload(dbbackup.settings)

        with pytest.raises(ValueError, match="Error during custom metadata validation:"):
            assert dbbackup.utils.validate_user_metadata({"CSMT_VAL": TEST_VAL}) is False
            assert False, "Should not reach this point"

    @override_settings(DBBACKUP_RESTORE_METADATA_VALIDATOR="tests.test_user_metadata.non_bool_validator")
    def test_metadata_validator_invalid_3(self):
        """Test that various validator missconfigurations do not work - Exception during validation."""
        importlib.reload(dbbackup.settings)

        with pytest.raises(TypeError, match="DBBACKUP_RESTORE_METADATA_VALIDATOR must return a boolean or None"):
            assert dbbackup.utils.validate_user_metadata({"CSMT_VAL": TEST_VAL}) is False
            assert False, "Should not reach this point"
