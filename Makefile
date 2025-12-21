.PHONY: update

update:
	rm -rf papers
	mkdir -p papers
	python src/convert.py data/records.bib papers
	colrev convert data/records.bib --format csv

citations:
	python src/citations.py


network:
	python src/extract_paper_network.py

