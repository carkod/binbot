# Linting

The backend formatting, lint and type-check commands are defined in the root
[Makefile](../Makefile). Run `make format` to apply configured fixes or
`make lint` to check without rewriting files. Tool configuration lives in
[pyproject.toml](../pyproject.toml) and [mypy.ini](../mypy.ini).

Terminal formatting, lint and type-check scripts are defined in
[terminal/package.json](../terminal/package.json).
