.PHONY: mlops robotics industrial sre telemetry stop validate validate-ci

mlops:
	npm run mlops:start

robotics:
	npm run robotics:start

industrial:
	npm run industrial:start

sre:
	npm run sre:start

telemetry:
	npm run telemetry:start

stop:
	npm run mlops:stop
	npm run telemetry:stop
	npm run sre:stop

validate:
	npm run validate

validate-ci:
	npm run validate:ci
