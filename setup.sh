#!/bin/sh

# Initial django migration
echo ""
echo "------------------------------------------------------------"
echo "Initial Django migration"
echo ""
python manage.py makemigrations
python manage.py migrate

# Initial fixtures
echo ""
echo "------------------------------------------------------------"
echo "Initial fixtures"
echo ""
python manage.py loaddata simple_click/fixtures/game.json
python manage.py loaddata simple_click/fixtures/market.json

echo ""
echo "------------------------------------------------------------"
echo "All Done!"
echo "------------------------------------------------------------"
echo ""
