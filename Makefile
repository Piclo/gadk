lint:
	mypy gadk/

test:
	tox

format:
	black gadk/

publish:
	rm -rf dist/ gadk.egg-info/
	poetry publish --build
