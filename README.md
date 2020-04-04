# Avarulo: Price Alert

This tool checks for prices of products in certain onlineshops and alerts you
if they drop below a certain price.

Price checks are implemented, alerting is not yet done.

## Usage

Setup venv

    python -m venv venv

Install dependencies

    venv/bin/pip install -U -r requirements.txt

Adjust `config.yml` with an editor of your choice, then run:

    venv/bin/python pricealert.py
