.PHONY: start
start:
	cd frontend && npm run dev
	cd backend && source .venv/bin/activate && python3 main.py

.PHONY: server
server:
	cd backend && source .venv/bin/activate && python3 main.py

.PHONY: client
client:
	cd frontend && npm run dev