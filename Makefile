black:
	poetry run black kanidm_operator

shell:
	env $(cat .env | grep -v "#" | xargs) poetry run python3 -m asyncio
