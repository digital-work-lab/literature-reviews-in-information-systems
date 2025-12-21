.PHONY: update

update:
	rm -rf papers
	mkdir -p papers
	python src/convert.py data/records.bib papers

citations:
	python src/citations.py


network:
	python src/extract_paper_network.py

