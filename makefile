.PHONY: start
start:
	./run-local.sh

.PHONY: install
install:
	cd backend && source .venv/bin/activate && pip3 install -r requirements.txt
	cd frontend && npm install

.PHONY: clean
clean:
	cd backend && rm -rf .venv
	cd frontend && rm -rf node_modules

.PHONY: clean-install
clean-install:
	make clean
	make install

.PHONY: stop
stop:
	./stop-local.sh

.PHONY: restart
restart:
	./stop-local.sh
	./run-local.sh

.PHONY: deploy
deploy:
	./deploy-backend-gcp.sh
	vercel --prod