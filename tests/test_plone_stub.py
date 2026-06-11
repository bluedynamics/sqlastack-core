"""Tests for the plone integration module."""

from __future__ import annotations


def test_import_plone_module():
    """sqlastack.plone must be importable."""
    import sqlastack.plone

    assert hasattr(sqlastack.plone, "HAS_ZOPE")


def test_has_zope_true_when_installed():
    """HAS_ZOPE should be True when zope.sqlalchemy is installed."""
    from sqlastack.plone import HAS_ZOPE

    assert HAS_ZOPE is True


def test_mark_changed_importable():
    """mark_changed should be importable from sqlastack.plone."""
    from sqlastack.plone import mark_changed

    assert callable(mark_changed)


def test_create_scoped_zope_session_importable():
    """create_scoped_zope_session should be importable from sqlastack.plone."""
    from sqlastack.plone import create_scoped_zope_session

    assert callable(create_scoped_zope_session)
