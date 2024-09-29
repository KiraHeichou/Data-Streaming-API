# Python Module that queries guardian API and push results to AWS msg broker
# config.ini file is used to store the api keys and other configurations
# Make sure all configuration parameters are filled in:
#   [guardian]
#   api_key = guardian API key
#   api_url = https://content.guardianapis.com/search
#   [aws]
#   access_key = aws_access_key
#   secret_key = aws_secret_key
#   region = us-east-1
#   retention_period = 72

# Requires requests, boto3, json, configparser and sys packages
# This tool can be invoked from commandline:
# python3 guardianapi.py "search term" "AWS kinesis id" "date from (opt)"
import requests  # To use the API access module to use guardian API
import boto3  # To interface with AWS
import json  # To use JSON
import configparser  # To read from configuration File
import sys  # To access commandline params


def get_guardian_articles(search_term, msg_broker_id, date_from=None):
    """
    Searches articles in the Guardian API with the search_term
    and publishes the results to a message broker with id msg_broker_id.

    input params:
        msg_broker_id (str): reference id of AWS message broker.
        search_term (str): The search term.
        date_from (str, optional): Date to filter articles from

    Returns:
        True if successful
    """

    try:
        # Read the configuration file to get the parameters
        config = configparser.ConfigParser()
        config.read('./config.ini')
    except Exception as excep:
        raise ValueError(f"Error reading config file config.ini-{excep}")

    try:
        # API configurations - Read URL and Key from config file
        API_URL = config.get('guardian', 'api_url')
        API_KEY = config.get('guardian', 'api_key')

        # print(API_KEY)
        # AWS message broker - Kinesis configuration
        # - access key, secret key, region and name of the stream
        # and retention period for the message in the broker
        AWS_ACCESS_KEY = config.get('aws', 'access_key')
        AWS_SECRET_KEY = config.get('aws', 'secret_key')
        AWS_REGION = config.get('aws', 'region', fallback='us-east-1')
        AWS_RETENTION_PRIOD = int(config.get('aws', 'retention_period'))
    except Exception as excep:
        raise ValueError(f"Missing configuration parameters in config.ini-\
                         {excep}")

    # raise an error if parameters are not present
    if not API_KEY or not AWS_ACCESS_KEY or not API_URL or \
       not AWS_SECRET_KEY or not AWS_RETENTION_PRIOD:
        raise ValueError("insufficient configuration parameters in config.ini")

    # set parameters for the API search
    params = {
        'q': search_term,
        'api-key': API_KEY,
        'page-size': 10,  # Limit to 10 results as per specification
    }
    if date_from:
        params['from-date'] = date_from

    try:
        # Call the API to get results from guardian for the search term
        response = requests.get(API_URL, params=params, timeout=10)
    except Exception as excep:
        raise Exception(f"Guardian API request failed-{excep}")

    # raise an exception if API call fails
    if response.status_code != 200:
        raise Exception(f"Guardian API request failed: {response.status_code} \
                        - {response.text}")

    # Convert the response from API calls into JSON format
    articles = response.json().get('response', {}).get('results', [])

    # Extract the fields to be posted as per specification
    article_details_to_post = [{'webPublicationDate':
                                item.get('webPublicationDate'),
                                'webTitle': item.get('webTitle'),
                                'webUrl': item.get('webUrl')}
                               for item in articles]
    # print(article_details_to_post)

    # Get the data to put into message stream as JSON
    data = json.dumps(article_details_to_post)

    # print(data)

    try:
        # Set parameters for message broker
        # Create a kinesis client with the credentials
        aws_msg_broker = boto3.client(
            'kinesis',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        str_summary = \
            aws_msg_broker.describe_stream_summary(StreamName=msg_broker_id)

        current_ret_period = \
            str_summary['StreamDescriptionSummary']['RetentionPeriodHours']
        # set message retention period (3 days as per specification)
        if current_ret_period > AWS_RETENTION_PRIOD:
            aws_msg_broker.decrease_stream_retention_period(
                StreamName=msg_broker_id,
                RetentionPeriodHours=AWS_RETENTION_PRIOD
            )

        if current_ret_period < AWS_RETENTION_PRIOD:
            aws_msg_broker.increase_stream_retention_period(
                StreamName=msg_broker_id,
                RetentionPeriodHours=AWS_RETENTION_PRIOD
            )

        # Post the data to message stream as JSON
        aws_msg_broker.put_record(
            StreamName=msg_broker_id,
            Data=data,
            PartitionKey="guardian api data"
        )
    except Exception as excep:
        raise Exception(f"AWS kinesis API call failure-{excep}")

    return True


def main(search_term, stream_id, date_from=None):
    """
    Main tool function to search articles and publish to Kinesis.

    Parameters:
        search_term (str): The search term.
        stream_id (str): The AWS kinesis stream id.
        date_from (str, optional): Date to filter articles from
    """
    # Search for articles using guardian API
    get_guardian_articles(search_term, stream_id, date_from)

# Ability to run from commandline:


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    # main("electric cars", "aws_stream")
