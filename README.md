# finances

Simple script for downloading recent transactions from Fio Bank and uploading them to spreadsheet in Google Docs.

## Status: ACTIVE

Under active development and maintenance.

## Installation

Download, run `pip install -r requirements.txt` and put the script to your `cron` settings (once a week, once a day maybe).
Create `config` JSON file according to `config.sample`. The Google password is base64-encoded (not secure at all,
but still better than plaintext).

## Usage

Downloads **latest** transactions and uploads them to spreadsheet:

    $ python finances.py

Downloads **all** transactions in your account's history and uploads them to spreadsheet:

    $ python finances.py --full

Prevents duplicates by checking transaction ID. For further information [read code](https://github.com/honzajavorek/finances/blob/master/finances.py).


## License: ISC

© 2013 Jan Javorek <jan.javorek@gmail.com>

This work is licensed under [ISC license](https://en.wikipedia.org/wiki/ISC_license).
