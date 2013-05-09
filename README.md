# finances

Simple script for downloading recent transactions from [Fio Bank](http://www.fio.cz/) and uploading them to spreadsheet in Google Docs.
Moreover, it also pairs transactions with invoices from [Fakturoid](http://fakturoid.cz/).

## Status: ACTIVE

Under active development and maintenance.

## Installation

Download, run `pip install -r requirements.txt` and put the script to your `cron` settings (once a week, once a day maybe).
Create `config` JSON file according to `config.sample`. The Google password is base64-encoded (not secure at all,
but still better than plaintext).

## Usage

Downloads **latest** transactions and uploads them to spreadsheet:

```bash
$ python finances.py
```

Downloads **all** transactions in your account's history and uploads them to spreadsheet:

```bash
$ python finances.py --full
```

Prevents duplicates by checking transaction ID. If transaction has variable
symbol and the amount is positive number (it is not expense), corresponding
invoice is searched and transaction data are populated with some additional
info from Fakturoid.

For further information [read code](https://github.com/honzajavorek/finances/blob/master/finances.py).


## License: ISC

© 2013 Jan Javorek <jan.javorek@gmail.com>

This work is licensed under [ISC license](https://en.wikipedia.org/wiki/ISC_license).
