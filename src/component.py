'''
Template Component main class.

'''

import logging
import logging_gelf.handlers
import logging_gelf.formatters
import sys
import os
import datetime  # noqa
import dateparser
import csv
import json
import requests
from urllib.parse import urlencode
import hashlib
from time import strftime, gmtime
import pandas as pd

from kbc.env_handler import KBCEnvHandler
from kbc.result import KBCTableDef  # noqa
from kbc.result import ResultWriter  # noqa


# configuration variables
KEY_AFFILIATE_ID = 'affiliate_id'
KEY_TOKEN = '#token'
KEY_SECRET_KEY = '#secret_key'
KEY_ENDPOINT = 'endpoint'
KEY_KEYWORD = 'keyword'
KEY_INCREMENTAL_PERIOD = 'incremental_period'
KEY_BACKFILL_MODE = 'backfill_mode'

MANDATORY_PARS = [
    KEY_AFFILIATE_ID,
    KEY_TOKEN,
    KEY_SECRET_KEY,
    KEY_ENDPOINT,
    KEY_KEYWORD,
    KEY_INCREMENTAL_PERIOD,
    KEY_BACKFILL_MODE
]
MANDATORY_IMAGE_PARS = []

# Default Table Output Destination
DEFAULT_TABLE_SOURCE = "/data/in/tables/"
DEFAULT_TABLE_DESTINATION = "/data/out/tables/"
DEFAULT_FILE_DESTINATION = "/data/out/files/"
DEFAULT_FILE_SOURCE = "/data/in/files/"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)-8s : [line:%(lineno)3s] %(message)s',
    datefmt="%Y-%m-%d %H:%M:%S")

if 'KBC_LOGGER_ADDR' in os.environ and 'KBC_LOGGER_PORT' in os.environ:

    logger = logging.getLogger()
    logging_gelf_handler = logging_gelf.handlers.GELFTCPSocketHandler(
        host=os.getenv('KBC_LOGGER_ADDR'), port=int(os.getenv('KBC_LOGGER_PORT')))
    logging_gelf_handler.setFormatter(
        logging_gelf.formatters.GELFFormatter(null_character=True))
    logger.addHandler(logging_gelf_handler)

    # remove default logging to stdout
    logger.removeHandler(logger.handlers[0])

APP_VERSION = '0.0.5'


class Component(KBCEnvHandler):

    def __init__(self, debug=False):
        KBCEnvHandler.__init__(self, MANDATORY_PARS)
        logging.info('Running version %s', APP_VERSION)
        logging.info('Loading configuration...')

        try:
            self.validate_config()
            self.validate_image_parameters(MANDATORY_IMAGE_PARS)
        except ValueError as e:
            logging.error(e)
            exit(1)

    def get_request(self, url, header):
        '''
        Dummy get Request
        '''

        r = requests.get(url=url, headers=header)

        if r.status_code not in [200, 201]:
            logging.error(f'Request Issue: {r.text}')
            sys.exit(1)

        return r.text

    def generate_signature(self, endpoint, date_object, keyword):
        '''
        Generate request signature required for the API
        Parameters:
            date_object = {
                'dateStart': 'mm/dd/yyyy',
                'dateEnd': 'mm/dd/yyyy'
            }
        '''

        # Timestamp for each request made
        request_timestamp = strftime('%a, %d %b %Y %H:%M:%S', gmtime())
        request_timestamp = request_timestamp + ' GMT'

        # Request Body
        request_body = {
            'affiliateId': self.affiliate_id,
            'token': self.token,
            'version': 2.3,
            'action': endpoint,
            'format': 'csv'
        }
        if date_object:
            for i in date_object:
                request_body[i] = date_object[i]
        if keyword:
            request_body['keyword'] = keyword

        request_body_encoded = urlencode(request_body)

        # Request Header
        signature = ('{0}:{1}:{2}:{3}'.format(
            self.token, request_timestamp, endpoint, self.secret_key)).encode('utf-8')
        signature_hash = hashlib.sha256(signature).hexdigest()
        request_header = {
            'x-ShareASale-Date': request_timestamp,
            'x-ShareASale-Authentication': signature_hash.upper()
        }

        return request_header, request_body_encoded

    def dates_request(self, start_date, end_date):
        '''
        Returns a list of dataes within the given range
        '''

        dates = []
        start_date_form = dateparser.parse(start_date)
        end_date_form = dateparser.parse(end_date)
        day_diff = (end_date_form-start_date_form).days
        temp_date = start_date_form
        day_n = 0
        if day_diff == 0:
            dates.append(temp_date.strftime('%m/%d/%Y'))
        while day_n < day_diff:
            dates.append(temp_date.strftime('%m/%d/%Y'))
            temp_date += datetime.timedelta(days=1)
            day_n += 1
            if day_n == day_diff:
                dates.append(temp_date.strftime('%m/%d/%Y'))

        return dates

    def generate_date(self, backfill_mode, incremental_period):
        '''
        Generate set of startDate and endDate for all requests
        '''

        if backfill_mode['backfill'] == 'enable':
            logging.info('Backfill Mode: Enable')
            # Error prevention
            if backfill_mode['start_date'] == '' or backfill_mode['end_date'] == '':
                logging.error(
                    'Start date or end date cannot be empty when backfill mode is enabled.')
                sys.exit(1)
            start_date = dateparser.parse(backfill_mode['start_date'])
            end_date = dateparser.parse(backfill_mode['end_date'])
        else:
            # start_date = dateparser.parse('2 days ago')
            start_date = dateparser.parse(incremental_period)
            end_date = dateparser.parse('today')

        if start_date > end_date:
            logging.error(
                'Start date cannot exceed end date. Please validate your date input.')
            sys.exit(1)

        start_date_form = start_date.strftime('%m/%d/%Y')
        end_date_form = end_date.strftime('%m/%d/%Y')
        date_object = {
            'dateStart': start_date_form,
            'dateEnd': end_date_form
        }

        return date_object

    def produce_manifest(self, file_name, primary_key, columns=None):
        """
        Dummy function to return header per file type.
        Parameters:
            1. file_name
            2. primary_key
            3. columns
                - the columns names in KBC
                - the output files have to be headerless
        """

        file = file_name + '.manifest'
        manifest = {
            "primary_key": primary_key
        }
        if columns:
            manifest['columns'] = columns

        try:
            with open(file, 'w') as file_out:
                json.dump(manifest, file_out)
                logging.info(f"Output manifest file [{file_name}]produced.")
        except Exception as e:
            logging.error("Could not produce output file manifest.")
            logging.error(e)

    def output_file(self, file_name, data_in, skip_header=False, expected_header=[],
                    add_date_column=None,
                    add_merchantId_column=None):
        '''
        Output method for files that need custom headers
        Parameters:
            1. skip_header
                - skipping header row in the data file
            2. expected_header
                - expected headers for the output file
            3. add_date_column
                - for files that need to add a new column, date, keyword
            4. add_merchantId_column
                - for endpoints that required to request merchantId as an additiaon parameter
        '''

        log_msg = file_name
        if add_date_column:
            log_msg = '{}-{}'.format(file_name, add_date_column)
        logging.info('Outputting [{}]...'.format(log_msg))
        with open(file_name, 'a') as f:
            if skip_header:
                writer = csv.writer(f)
                temp_data = csv.reader(data_in.splitlines())
                header = next(temp_data)

                # Appending parent_id column
                if add_merchantId_column:
                    header.append(add_merchantId_column)
                if add_date_column:
                    header.append(add_date_column)

                # Header Validation
                if len(header) != len(expected_header):
                    logging.error(
                        "There are more columns than expected columns for [{}]".format(file_name))
                    logging.error("New columns: {}".format(
                        header-expected_header))
                    logging.error("Please contact support.")
                    sys.exit(1)

                for row in temp_data:
                    if add_merchantId_column:
                        row.append(add_merchantId_column)
                    if add_date_column:
                        row.append(add_date_column)
                    writer.writerow(row)
            else:
                # Breaking up all the lines
                writer = csv.writer(f)
                temp_data = data_in.splitlines()

                for row in temp_data:
                    logging.info(f'ROW: {row}')
                    if row.strip() != '':
                        writer.writerow(data_in)
                # f.write(data_in)
        f.close()

    def output_process(self, data_in, endpoint, endpoint_config, date_column='', merchantId=''):
        '''
        Request Output Validation
        Defining output method based on endpoint selected
        Issue:
            1.  all requests will return 200 regardless invalid parameters
                If there is only one row, assuming it is an error message
            2.  If endpoint is merchant_timespan, will need to break up
                the output file as sliced files
        Parameters:
            date_column
                - to handle any files that need to have a extra column value
                - does not have to be a date, can be a keyword column for getProducts
            merchantId
                - to handle any endpoints that need to send in additiaon merchantId as a parameter
        '''

        num_of_rows = len(data_in.splitlines())

        if (num_of_rows == 1
            and endpoint not in ['getProducts', 'merchantTimespan', 'traffic_by_afftrack']
                and 'Error Code' in data_in):
            logging.error(
                'Endpoint request failed: [{}]; Error message: [{}]'.format(endpoint, data_in))
            logging.error('Please contact support.')
            sys.exit(1)

        elif endpoint in ['getProducts', 'merchantTimespan', 'traffic', 'traffic_by_afftrack']:
            output_file_name = '{0}{1}.csv'.format(
                DEFAULT_TABLE_DESTINATION, endpoint_config['name'])
            expected_header = endpoint_config['columns']

            if endpoint in ['traffic_by_afftrack']:
                self.output_file(output_file_name, data_in,
                                 skip_header=True,
                                 expected_header=expected_header,
                                 add_date_column=date_column,
                                 add_merchantId_column=merchantId)
            else:
                self.output_file(output_file_name, data_in,
                                 skip_header=True,
                                 expected_header=expected_header,
                                 add_date_column=date_column)
            self.produce_manifest(
                output_file_name, endpoint_config['primary_key'], expected_header)

        else:
            output_file_name = '{0}{1}.csv'.format(
                DEFAULT_TABLE_DESTINATION, endpoint_config['name'])
            self.output_file(output_file_name, data_in)
            self.produce_manifest(
                output_file_name, endpoint_config['primary_key'])

    def run(self):
        '''
        Main execution code
        '''

        # Credentials and request params
        params = self.cfg_params  # noqa
        # Validating if there are any params:
        if params == {}:
            logging.error('Please enter and save your required parameters.')
            sys.exit(1)

        # Component configuration parameters
        self.affiliate_id = params[KEY_AFFILIATE_ID]
        self.token = params[KEY_TOKEN]
        self.secret_key = params['#secret_key']
        endpoints = params['endpoint']
        keyword = params['keyword']
        backfill_mode = params['backfill_mode']
        incremental_period = params[KEY_INCREMENTAL_PERIOD]
        request_date = self.generate_date(backfill_mode, incremental_period)
        base_url = 'https://api.shareasale.com/x.cfm'
        # Input Tables
        self.input_tables = []
        for i in self.configuration.get_input_tables():
            table_full_path = i['full_path']
            self.input_tables.append(table_full_path)

        # Validating user inputs
        if self.affiliate_id == '' or self.token == '' or self.secret_key == '':
            logging.error(
                'Please enter required parameters: Affiliate ID, Token, Secret Key')
            sys.exit(1)
        if len(endpoints) == 0:
            logging.error('Please specify [Endpoints].')
            sys.exit(1)

        # Validate if input mapping is configured
        # when endpoint [traffic by afftrack] is selected
        for i in endpoints:
            if i['endpoint'] == 'traffic_by_afftrack':
                if len(self.input_tables) == 0:
                    logging.error(
                        'Endpoint [Traffic - Merchant grouped by Afftrack] requires Input Tables.')
                    sys.exit(1)
                else:
                    for table in self.input_tables:
                        df = pd.read_csv(table, nrows=1)
                        required_column = 'merchantID'
                        if required_column not in df.columns:
                            logging.error(
                                f'Required column [{required_column}] is missing in [{table}]')
                            sys.exit(1)

        logging.info(
            "Request date range: {0} - {1}".format(request_date['dateStart'], request_date['dateEnd']))

        # Fetching mapping configuration required for each endpoint
        with open('src/mapping.json', 'r') as f:
            config_mapping = json.load(f)

        # Endpoint Requests
        for i in endpoints:
            endpoint = i["endpoint"]
            endpoint_config = config_mapping[endpoint]
            endpoint_url = endpoint_config['url']
            logging.info('Parsing [{}]...'.format(endpoint_config['name']))

            # Handle required parameters
            date_to_request = None
            keyword_to_request = None
            if endpoint_config['date_required']:
                date_to_request = request_date
            if endpoint_config['keyword_required']:
                if keyword == '':
                    logging.error(
                        'A keyword value is required for [{}]. Please enter a keyword or phrase.'.format(endpoint))
                    sys.exit(1)
                keyword_to_request = keyword

            if endpoint in ['merchantTimespan', 'traffic']:
                date_range = self.dates_request(request_date['dateStart'], request_date[
                    'dateEnd'
                ])
                # Looping thru the dates in the date range for daily stats
                for date in date_range:
                    temp_date_obj = {
                        'dateStart': date,
                        'dateEnd': date
                    }
                    request_header, request_body = self.generate_signature(
                        endpoint=endpoint_url, date_object=temp_date_obj, keyword=keyword_to_request)
                    request_url = base_url+'?'+request_body
                    data_in = self.get_request(request_url, request_header)
                    self.output_process(data_in, endpoint,
                                        endpoint_config, date)

            elif endpoint in ['traffic_by_afftrack']:
                date_range = self.dates_request(
                    request_date['dateStart'], request_date['dateEnd'])

                # Loop thru Input tables
                for table in self.input_tables:
                    merchant_data = pd.read_csv(table)

                    # Every Input Merchant
                    for merchant in merchant_data['merchantID']:
                        # Every date in date range
                        for date in date_range:
                            temp_date_obj = {
                                'dateStart': date,
                                'dateEnd': date,
                                'merchantId': merchant,
                                'groupBy': 'afftrack'
                            }
                            request_header, request_body = self.generate_signature(
                                endpoint=endpoint_url, date_object=temp_date_obj, keyword=keyword_to_request)
                            request_url = base_url+'?'+request_body
                            data_in = self.get_request(
                                request_url, request_header)
                            self.output_process(data_in, endpoint,
                                                endpoint_config, date, merchant)

            else:
                request_header, request_body = self.generate_signature(
                    endpoint=endpoint_url, date_object=date_to_request, keyword=keyword_to_request)
                request_url = base_url+'?'+request_body
                data_in = self.get_request(request_url, request_header)
                self.output_process(data_in, endpoint,
                                    endpoint_config, keyword_to_request)

        logging.info("Extraction finished")


"""
        Main entrypoint
"""
if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug = sys.argv[1]
    else:
        debug = True
    comp = Component(debug)
    comp.run()
