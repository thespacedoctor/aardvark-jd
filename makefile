fulltest:
	pytest -v -s --profile-svg --profile
	for i in prof/*.prof; do gprof2dot -f pstats $i | dot -Tsvg -o $i.svg; done

litetest:
	pytest  -m "not full" -v -s --profile-svg --profile
	for i in prof/*.prof; do gprof2dot -f pstats $i | dot -Tsvg -o $i.svg; done

# COVERAGE, SO THE 80 PER CENT BAR IS REPRODUCIBLE RATHER THAN REMEMBERED.
# THE BAR IS PER MODULE, NOT GLOBAL - A GLOBAL AVERAGE LETS A WELL-TESTED
# `db.py` HIDE AN UNTESTED NEW MODULE.
test-cov:
	pytest -m "not full" --cov=aardvark_jd --cov-report=term-missing

# SORT `info.plist`'s `objects` ARRAY BY `uid`, SO ALFRED'S REORDERING ON
# EVERY EDIT STOPS SHOWING UP AS DIFF NOISE. RUN BY HAND AFTER EDITING THE
# WORKFLOW IN ALFRED AND BEFORE READING THE DIFF - DELIBERATELY NOT A GIT
# HOOK, SINCE AN AUTOMATIC REWRITE FIRING WHILE ALFRED HOLDS THE WORKFLOW
# OPEN IS A WAY TO LOSE AN EDIT.
alfred-normalise:
	python -m aardvark_jd.alfred.normalise aardvark_jd/resources/alfred/info.plist
