all:
	rm -f dist/*
	python3 setup.py sdist bdist_wheel

upload:
	python3 -m twine upload dist/* 

install:
	(cd ~ && sudo python3 -m pip install --upgrade patas)

uninstall:
	sudo pip uninstall patas -y

localinstall: uninstall all
	sudo pip install ./dist/patas-*-py3-none-any.whl

getdeps:
	python3 -m pip install --user --upgrade setuptools wheel
	python3 -m pip install --user --upgrade twine
	keyring --disable

test-pdb:
	pytest --rootdir tests --pdb

test:
	pytest --rootdir tests
