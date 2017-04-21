# coding=utf-8
"""
USAGE:
    python up.py /path/to/statement.csv
"""
from __future__ import print_function
import csv
from datetime import datetime
from collections import namedtuple, defaultdict
import urllib
import xml.etree.ElementTree as ET
import argparse

Row = namedtuple('Row', ['date', 'id', 'type', 'description', 'agency',
                         'freelancer', 'team', 'account', 'po', 'amount',
                         'amount_local', 'currency', 'balance', 'rate'])


def get_exchange_rate(date):
    # d=0 Коды валют устанавливаемые ежедневно.
    url = 'http://www.cbr.ru/scripts/XML_daily_eng.asp?d=0&date_req={date}'
    rate = get_exchange_rate.cache.get(date)

    if rate is None:
        r = urllib.urlopen(url.format(date=date.strftime('%d/%m/%Y')))
        for el in ET.parse(r).getroot():
            if el.find('CharCode').text == 'USD':
                rate = float(el.find('Value').text.replace(',', '.'))
                get_exchange_rate.cache[date] = rate
                break

    return rate

get_exchange_rate.cache = dict()


def read_csv(filename):
    transactions = defaultdict(dict)

    with open(filename) as f:
        reader = csv.reader(f, delimiter=',', quotechar='"')
        for row in reader:
            # Skip header and Withdrawal Fee.
            if row[0] == 'Date' or row[2].startswith('Withdrawal'):
                continue

            date = datetime.strptime(row[0], '%b %d, %Y').date()

            # Add to container grouped by type and date.
            # Additionally retrieve USD->RUB rate for the date.
            by_type = transactions[row[2]]
            by_date = by_type.setdefault(date, dict())
            rate = by_date['rate'] = get_exchange_rate(date)
            row.append(rate)

            # Create row.
            row[0] = date                       # date
            row[9] = abs(float(row[9]))         # amount
            row[10] = round(row[9] * rate, 2)   # amount_local
            row[12] = abs(float(row[12]))       # balance
            r = Row(*row)

            by_date.setdefault('items', []).append(r)
            by_date['total_rub'] = by_date.get('total_rub', 0) + r.amount_local
            by_date['total_usd'] = by_date.get('total_usd', 0) + r.amount

    return transactions


class TransactionWriter(object):
    def __init__(self, transaction_info, name):
        self.name = name
        self.transaction_info = transaction_info

    def do_write_header(self):
        pass

    def do_write_before(self, date_str, info):
        pass

    def do_write(self, date_str, item):
        pass

    def do_write_after(self, date_str, info):
        pass

    def write(self):
        if not self.transaction_info:
            return

        self.do_write_header()

        for date in sorted(self.transaction_info.keys()):
            date_str = date.strftime('%d.%m.%Y')
            date_info = self.transaction_info[date]

            self.do_write_before(date_str, date_info)

            items = date_info['items']
            items.sort(key=lambda x: x.team)
            for item in items:
                self.do_write(date_str, item)

            self.do_write_after(date_str, date_info)


class EarningsWriter(TransactionWriter):
    def __init__(self, transaction_info, name):
        super(EarningsWriter, self).__init__(transaction_info, name)
        self.offset = None

    def do_write_header(self):
        print(self.name)
        print('-' * max(len(self.name), 4))

    def do_write_before(self, date_str, info):
        print(date_str)
        self.offset = ' ' * len(date_str)

    def do_write(self, date_str, item):
        print('{offset}{team}\t {usd:0.2f} USD\t {rub:0.2f} RUB'.format(
            offset=self.offset, team=item.team, usd=item.amount,
            rub=item.amount_local))

    def do_write_after(self, date_str, info):
        print('\n{offset}total: {usd:0.2f} USD'.format(
            offset=self.offset, usd=info['total_usd']))
        print('{offset}total: {rub:0.2f} RUB\n'.format(
            offset=self.offset, rub=info['total_rub']))


class FeesWriter(EarningsWriter):
    def add_vat(self, text, amount):
        vat = round(amount * 0.18, 2)
        with_vat = amount + vat
        return text + '   \tVAT: {:0.2f} (total: {:0.2f}) RUB'.format(
            vat, with_vat)

    def do_write(self, date_str, item):
        txt = '{offset}{team}\t {usd:0.2f} USD\t {rub:0.2f} RUB'.format(
            offset=self.offset, team=item.team, usd=item.amount,
            rub=item.amount_local)
        print(self.add_vat(txt, item.amount_local))

    def do_write_after(self, date_str, info):
        print('\n{offset}total: {usd:0.2f} USD'.format(
            offset=self.offset, usd=info['total_usd']))
        txt = '{offset}total: {rub:0.2f} RUB'.format(
            offset=self.offset, rub=info['total_rub'])
        print(self.add_vat(txt, info['total_rub']))
        print('')


def cli():
    parser = argparse.ArgumentParser(description='Upwork earnings & VAT')
    parser.add_argument('filename', help='Transactions CSV filename.')
    args = parser.parse_args()

    transactions = read_csv(args.filename)

    for type in transactions.keys():
        if 'fee' in type.lower():
            FeesWriter(transactions[type], type).write()
        else:
            EarningsWriter(transactions[type], type).write()


if __name__ == '__main__':
    cli()
