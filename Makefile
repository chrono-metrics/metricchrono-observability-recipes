.PHONY: mlops robotics industrial telemetry stop validate validate-ci

mlops:
	npm run mlops:start

robotics:
	npm run robotics:start

industrial:
	npm run industrial:start

telemetry:
	npm run telemetry:start

stop:
	npm run mlops:stop
	npm run telemetry:stop

validate:
	npm run validate

validate-ci:
	npm run validate:ci
