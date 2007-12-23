# This Makefile is used to create an aspen distribution. Before calling, set the
# VERSION environment variable.

VERSION=0.8
DATE=December 23, 2007

UPDATE_VERSION=sed -e 's/~~VERSION~~/$(VERSION)/g' -i ''
UPDATE_DATE=sed -e 's/~~DATE~~/$(DATE)/g' -i ''


clean:
# remove all of the cruft that gets auto-generated on doc/install/release
	rm -rf build
	rm -rf dist
	find . -name \*.pyc | xargs rm
	make -C doc/tex clean

distclean: clean
# remove the final generated docs as well
	make -C doc/tex distclean

# Target for building a distribution
# ==================================
# note the dependency on svneol: http://www.zetadev.com/svn/public/svneol/

stamp:
	$(UPDATE_VERSION) README
	$(UPDATE_VERSION) doc/tex/Makefile
	$(UPDATE_VERSION) doc/tex/aspen.tex
	$(UPDATE_VERSION) doc/tex/installation.tex
	$(UPDATE_VERSION) doc/HISTORY
	$(UPDATE_VERSION) doc/CONTRIBUTORS
	$(UPDATE_VERSION) setup.py
	$(UPDATE_VERSION) lib/python/aspen/__init__.py

	$(UPDATE_DATE) README
	$(UPDATE_DATE) doc/HISTORY
	$(UPDATE_DATE) doc/CONTRIBUTORS
	$(UPDATE_DATE) doc/tex/aspen.tex

dist: distclean
	mkdir dist
	mkdir dist/aspen-${VERSION}
	cp -r README \
	      lib \
	      setup.py \
	      dist/aspen-${VERSION}

	make -C doc/tex all clean
	mkdir dist/aspen-${VERSION}/doc
	cp -r doc/html \
	      doc/aspen-${VERSION}.pdf \
	      doc/HISTORY \
	      dist/aspen-${VERSION}/doc

	mkdir dist/aspen-${VERSION}/bin
	cp -r bin/aspen \
	      dist/aspen-${VERSION}/bin

	mkdir dist/aspen-${VERSION}/etc
	cp -r etc/aspen_bash_completion \
	      dist/aspen-${VERSION}/etc

	tar --directory dist -zcf dist/aspen-${VERSION}.tgz aspen-${VERSION}
	tar --directory dist -jcf dist/aspen-${VERSION}.tbz aspen-${VERSION}

# ZIP archive gets different line endings
	svneol clean -w dist/aspen-${VERSION}
	cd dist && zip -9rq aspen-${VERSION}.zip aspen-${VERSION}
#	rm -rf dist/aspen-${VERSION}
