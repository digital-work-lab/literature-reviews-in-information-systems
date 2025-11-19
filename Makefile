.PHONY: update

update:
	rm -rf papers
	mkdir -p papers
	python src/convert.py records.bib papers
	colrev convert records.bib --format csv
