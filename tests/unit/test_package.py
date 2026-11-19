"""Package smoke tests."""


def test_package_is_importable() -> None:
    """Ensure the generated package is importable."""
    import solar_dispatch  # noqa: F401
