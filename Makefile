build: clean
	python3 setup.py sdist bdist_wheel

clean:
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	rm -rf *.pyc
	rm -rf __pycache__
	rm -rf fstringen/__pycache__

upload: clean test build
	python3 -m twine upload dist/*

test:
	pytest
