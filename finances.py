# -*- coding: utf-8 -*-


import sys
import json
import base64
import urllib2
import logging
from os import path
from functools import wraps
from datetime import date, timedelta

import fiobank
import gspread
from gevent.pool import Pool


from gevent import monkey
monkey.patch_all()


def read_config(filename):
    with open(filename) as f:
        return json.loads(f.read())


config = read_config(path.join(path.dirname(path.abspath(__file__)), 'config'))
logging.basicConfig(format=config['logging_format'],
                    level=getattr(logging, config['logging_level']))


def retry_on_conflict(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except urllib2.HTTPError as e:
            if e.code == 409:
                logging.debug(e)
                return retry_on_conflict(fn)(*args, **kwargs)
            else:
                raise
    return wrapper


class Spreadsheet(object):

    def __init__(self, username, password, spreadsheet_key):
        g = gspread.login(username, password)
        spreadsheet = g.open_by_key(spreadsheet_key)

        worksheet = spreadsheet.worksheet(config['worksheet_name'])
        header = worksheet.row_values(1)

        self.worksheet = worksheet
        self.header = header

        id_column = header.index('transaction_id') + 1
        self.ids = worksheet.col_values(id_column)

    @retry_on_conflict
    def append(self, data):
        worksheet = self.worksheet
        trans_id = data['transaction_id']

        if trans_id in self.ids:
            logging.info("Transaction '%s' already present.", trans_id)
            return  # transaction already exists in worksheet

        row = []
        for key in self.header:
            row.append(data.get(key, ''))

        worksheet.append_row(row)
        self.ids.append(trans_id)
        logging.info("Transaction '%s' saved.", trans_id)


def main(full=False):
    end_date = date.today()
    start_date = end_date - timedelta(days=50000 if full else 30)

    fio = fiobank.FioBank(config['fiobank_token'])
    transactions = fio.period(start_date, end_date)

    password = base64.b64decode(config['google_password'])
    spreadsheet = Spreadsheet(config['google_username'], password,
                              config['spreadsheet_key'])
    logging.info('Spreadsheet has %d transactions.', len(spreadsheet.ids))

    pool = Pool(config['max_concurrency'])
    pool.map(spreadsheet.append, transactions)
    pool.join()

    logging.info('Spreadsheet has %d transactions.', len(spreadsheet.ids))


if __name__ == '__main__':
    main('--full' in sys.argv)
