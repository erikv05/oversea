.PHONY: start
start:
	cd frontend && npm run dev
	cd backend && source .venv/bin/activate && python3 main.py