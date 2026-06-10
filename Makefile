FACE_MODEL ?= 4

.PHONY: download-models serve compose-up compose-down help

help:
	@echo "Targets:"
	@echo "  make download-models   Download the dlib .dat model files into vendor/models/"
	@echo "  make serve             Run locally via flask (requires download-models first)"
	@echo "  make compose-up        Build and start the docker-compose stack"
	@echo "  make compose-down      Stop the docker-compose stack"
	@echo ""
	@echo "Variables:"
	@echo "  FACE_MODEL=1|3|4       Detection algorithm (default 4)"
	@echo "  GUNICORN_WORKERS=N     Parallelism in the container (default 1)"

download-models serve:
	$(MAKE) -C docker $@ FACE_MODEL=$(FACE_MODEL)

compose-up compose-down:
	$(MAKE) -C docker $@
