"""Tests for the plone integration stub."""

from __future__ import annotations


def test_import_plone_module():
    """sqlastack.plone must be importable without Zope installed."""
    import sqlastack.plone

    assert hasattr(sqlastack.plone, "HAS_ZOPE")


def test_has_zope_false_without_zope():
    """HAS_ZOPE should be False when Zope is not installed."""
    from sqlastack.plone import HAS_ZOPE

    assert HAS_ZOPE is False
