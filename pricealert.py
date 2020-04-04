"""
Price Alert

Monitor products for price reductions.

Usage:
    pricealert.py [-c <configfile>]

Options:
    -c <configfile> [default: config.yml]

"""
import re
import sys
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from docopt import docopt
import requests
import yaml


USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:74.0) Gecko/20100101 Firefox/74.0'


def fetch(url: str, raw: bool = False) -> BeautifulSoup:
    response = requests.get(url, headers={'User-Agent': USER_AGENT})
    response.raise_for_status()
    if raw:
        return response.text
    return BeautifulSoup(response.text, 'html.parser')


def check_galaxus(url: str) -> Tuple[float, Optional[float]]:
    """
    Check the price on galaxus.ch.

    Current price:

        <meta content="49" property="product:price:amount"/>

    Regular price:

        <meta content="72.4" property="og:price:standard_amount"/>

    """
    soup = fetch(url)
    current = float(soup.find('meta', property='product:price:amount').get('content'))
    standard_amount_meta = soup.find('meta', property='og:price:standard_amount')
    if standard_amount_meta:
        regular = float(standard_amount_meta.get('content'))  # type: Optional[float]
    else:
        regular = None
    return (current, regular)


def check_baechli(url: str) -> Tuple[float, Optional[float]]:
    """
    Check the price on baechli-bergsport.ch.

    Current price:

        <meta content="49" property="product:price:amount"/>

    Regular price: ??

    """
    soup = fetch(url)
    current = float(soup.find('meta', property='product:price:amount').get('content'))
    return (current, None)


def check_intersport(url: str) -> Tuple[float, Optional[float]]:
    """
    Check the price on achermannsport.ch.

    Raw data:

        <div class="summary entry-summary">
         <h1 class="product_title entry-title">Ligtning Ascent 22 Women raspberry und Gunmetal</h1>
         <p class="price">
          <del><span class="woocommerce-Price-amount amount"><span class="woocommerce-Price-currencySymbol">&#67;&#72;&#70;</span>&nbsp;379.00</span></del>
          <ins><span class="woocommerce-Price-amount amount"><span class="woocommerce-Price-currencySymbol">&#67;&#72;&#70;</span>&nbsp;299.90</span></ins>
         </p>
         ...

    Raw data (no rebate):

        <div class="summary entry-summary">
         <h1 class="product_title entry-title">Ligtning Ascent 22 Women raspberry und Gunmetal</h1>
         <p class="price">
          <span class="woocommerce-Price-amount amount"><span class="woocommerce-Price-currencySymbol">&#67;&#72;&#70;</span>&nbsp;29.00</span>
         </p>
         ...

    """
    soup = fetch(url)
    summary = soup.find('div', class_='entry-summary')
    prices = summary.find(class_='price')
    regular = prices.find('del', recursive=False)
    current = prices.find('ins', recursive=False)

    def _get_price(element) -> float:
        parts = element.find(class_='amount').text.split('\xa0')
        assert parts[0] == 'CHF'
        return float(parts[1])

    if regular and current:
        return (_get_price(current), _get_price(regular))
    else:
        return (_get_price(prices), None)


def check_primal(url: str) -> Tuple[float, Optional[float]]:
    """
    Check the price on primal.ch.

    Current price:

        <meta itemprop="price" content="284.90">

    Regular price:

        <span class="price--line-through">CHF&nbsp;469.00 *</span>

    """
    soup = fetch(url)
    current = float(soup.find('meta', itemprop='price').get('content'))
    regular_element = soup.find('span', class_='price--line-through')
    if regular_element:
        regular = float(re.findall(r'[\d\.]+', regular_element.text)[0])
        return (current, regular)
    else:
        return (current, None)


def check_transa(url: str) -> Tuple[float, Optional[float]]:
    """
    Check the price on transa.ch.

    Non-promo:

        price: {
          base: '',
          promo: 'CHF 379.90',
          savings: 'CHF 0.00',
          reducedPriceInfoText: 'Streichpreis entspricht dem zuletzt angezeigten Preis im Onlineshop.',
          basicPrice: ''
        },

    Promo:

        price: {
          base: 'CHF 899.90',
          promo: 'CHF 629.90',
          savings: 'CHF 270.00',
          reducedPriceInfoText: 'Streichpreis entspricht dem zuletzt angezeigten Preis im Onlineshop.',
          basicPrice: ''
        },

    """
    text = fetch(url, raw=True)
    prices = {}
    matches = filter(
        None,
        [re.match(r"^\s*(base|promo): 'CHF ([^']*)',$", line) for line in text.splitlines()],
    )
    for match in matches:
        prices[match.group(1)] = float(match.group(2))
    return (prices['promo'], prices.get('base'))


def _load_check_fn(shop: dict) -> dict:
    """
    Load a check function by name.
    """
    func = globals().get(shop['check_func'])
    if func is None:
        raise ValueError('Check func not found: {}'.format(shop['check_func']))
    shop['check_func'] = func
    return shop


def main(config: dict):
    # Load shops
    shops = {
        k: _load_check_fn(v)
        for k, v
        in config['shops'].items()
    }

    for product in config['products']:
        print('Checking {}:'.format(product['name']))
        for shop_id, url in product['shops'].items():
            shop = shops[shop_id]
            prices = shop['check_func'](url)
            print('  {}: {:.2f} CHF'.format(shop['name'], prices[0]), end='')
            if prices[1] is None:
                print()
            else:
                assert prices[1] > prices[0], prices
                print(' (statt {:.2f} CHF)'.format(prices[1]))
        print()


if __name__ == '__main__':
    args = docopt(__doc__, version='Price Alert 0.1')

    configfile = args['-c'] or 'config.yml'
    with open(configfile, 'r') as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print('Could not load config file: {}'.format(e))
            sys.exit(1)

    main(config)
