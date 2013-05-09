# -*- coding: utf-8 -*-


import sys
import json
import base64
import urllib2
import httplib
import logging
import itertools
from os import path
from functools import wraps
from datetime import date, timedelta

import fiobank
import gspread
import requests
from gevent.pool import Pool


from gevent import monkey
monkey.patch_all()


def read_config(filename):
    with open(filename) as f:
        return json.loads(f.read())


config = read_config(path.join(path.dirname(path.abspath(__file__)), 'config'))
logging.basicConfig(format=config['logging_format'],
                    level=getattr(logging, config['logging_level']))


def retry_on_error(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except urllib2.HTTPError as e:
            if e.code == 409:
                logging.debug(e)
                return retry_on_error(fn)(*args, **kwargs)
            else:
                raise
        except (IOError, httplib.HTTPException) as e:
            logging.debug(e)
            return retry_on_error(fn)(*args, **kwargs)
    return wrapper


def concurrent_map(fn, iterable, concurrency=None):
    pool = Pool(concurrency or config['max_concurrency'])
    pool.map(fn, iterable)
    pool.join()


class Spreadsheet(object):

    def __init__(self, username, password, spreadsheet_key, worksheet_name):
        g = gspread.login(username, password)
        spreadsheet = g.open_by_key(spreadsheet_key)

        worksheet = spreadsheet.worksheet(worksheet_name)
        header = worksheet.row_values(1)

        self.worksheet = worksheet
        self.header = header

        id_column = header.index('transaction_id') + 1
        self.ids = worksheet.col_values(id_column)[1:]

    @retry_on_error
    def append(self, data):
        worksheet = self.worksheet
        trans_id = data['transaction_id']

        if trans_id in self.ids:
            logging.info("Transaction '%s' already present.", trans_id)
            return  # transaction already exists in worksheet

        row = []
        for key in self.header:
            row.append(data.get(key) or '')

        worksheet.append_row(row)
        self.ids.append(trans_id)
        logging.info("Transaction '%s' saved.", trans_id)


class Fakturoid(object):

    base_url = 'https://{subdomain}.fakturoid.cz/api/v1/'

    def __init__(self, subdomain, token, load_size=None):
        self.load_size = load_size or config['max_concurrency']
        self.base_url = self.base_url.format(subdomain=subdomain)
        self.token = token

        self._invoices = None

    @property
    def invoices(self):
        if self._invoices is None:
            invoices = {}
            load_size = self.load_size

            def load_invoice(page):
                data = self._request('invoices.json', page=page)
                for invoice in data:
                    vs = str(invoice['variable_symbol'])
                    invoices[vs] = invoice

            for batch in itertools.count(0):
                count_before = len(invoices)

                pages = range(batch * load_size + 1,
                              batch * load_size + load_size)
                concurrent_map(load_invoice, pages, concurrency=load_size)

                count_after = len(invoices)
                if count_after == count_before:
                    break

            self._invoices = invoices
        return self._invoices

    def _request(self, path, **params):
        response = requests.get(self.base_url + path, params=params,
                                auth=('', self.token))
        response.raise_for_status()
        return response.json()

    def invoice(self, vs):
        return self.invoices.get(str(vs))

    def populate_transaction(self, trans):
        if trans and trans.get('variable_symbol') and trans.get('amount') > 0:
            inv = self.invoice(trans['variable_symbol'])
            if inv:
                trans['invoice_id'] = inv['id']
                trans['invoice_number'] = inv['number']
                trans['client_name'] = inv['client_name']
                trans['client_registration_no'] = inv['client_registration_no']
                trans['invoice_issued_on'] = (inv.get('issued_on') or '')[:10]
                trans['invoice_sent_at'] = (inv.get('sent_at') or '')[:10]
        return trans


def main(full=False):
    end_date = date.today()
    start_date = end_date - timedelta(days=50000 if full else 30)

    fio = fiobank.FioBank(config['fiobank_token'])
    transactions = fio.period(start_date, end_date)

    password = base64.b64decode(config['google_password'])
    spreadsheet = Spreadsheet(config['google_username'], password,
                              config['spreadsheet_key'],
                              config['worksheet_name'])

    fakturoid = Fakturoid(config['fakturoid_subdomain'],
                          config['fakturoid_token'])

    logging.info('Spreadsheet has %d transactions.', len(spreadsheet.ids))
    concurrent_map(
        lambda t: spreadsheet.append(fakturoid.populate_transaction(t)),
        transactions
    )
    logging.info('Spreadsheet has %d transactions.', len(spreadsheet.ids))


if __name__ == '__main__':
    main('--full' in sys.argv)
