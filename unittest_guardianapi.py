import unittest
from unittest.mock import patch, MagicMock
import configparser
import json
from guardianapi import get_guardian_articles


class TestGuardianArticles(unittest.TestCase):

    @patch('guardianapi.boto3.client')  # Mock the boto3 client
    @patch('guardianapi.requests.get')  # Mock the requests.get call
    @patch('guardianapi.configparser.ConfigParser')  # Mock configparser
    def test_get_guardian_articles_success(
            self, mock_config_parser, mock_requests_get, mock_boto_client):
        # Mock the configuration parser to provide necessary parameters
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda section, key, fallback=None: {
            ('guardian', 'api_url'): 'https://content.guardianapis.com/search',
            ('guardian', 'api_key'): 'dummy_api_key',
            ('aws', 'access_key'): 'dummy_access_key',
            ('aws', 'secret_key'): 'dummy_secret_key',
            ('aws', 'region'): 'us-east-1',
            ('aws', 'retention_period'): '72'
        }[(section, key)]
        mock_config_parser.return_value = mock_config

        # Mock the response from the Guardian API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': {
                'results': [
                    {
                        'webPublicationDate': '2024-01-01T12:00:00Z',
                        'webTitle': 'Test Article',
                        'webUrl': 'https://example.com/test-article'
                    }
                ]
            }
        }
        mock_requests_get.return_value = mock_response

        # Mock the AWS Kinesis client and its methods
        mock_kinesis_client = MagicMock()
        mock_boto_client.return_value = mock_kinesis_client
        mock_kinesis_client.describe_stream_summary.return_value = {
            'StreamDescriptionSummary': {
                'RetentionPeriodHours': 24  # Current retention period<desired
            }
        }

        # Call the function to test
        result = get_guardian_articles(
            'test', 'test-stream', date_from='2024-01-01')

        # Verify the Guardian API call
        mock_requests_get.assert_called_once_with(
            'https://content.guardianapis.com/search',
            params={'q': 'test', 'api-key': 'dummy_api_key', 'page-size': 10,
                    'from-date': '2024-01-01'},
            timeout=10
        )

        # Verify the Kinesis client was called to set the retention period
        mock_kinesis_client.increase_stream_retention_period\
            .assert_called_once_with(
                StreamName='test-stream',
                RetentionPeriodHours=72
            )

        # Verify the put_record call
        mock_kinesis_client.put_record.assert_called_once_with(
            StreamName='test-stream',
            Data=json.dumps([{
                'webPublicationDate': '2024-01-01T12:00:00Z',
                'webTitle': 'Test Article',
                'webUrl': 'https://example.com/test-article'
            }]),
            PartitionKey="guardian api data"
        )

        # Check that the function returns True
        self.assertTrue(result)

    @patch('guardianapi.configparser.ConfigParser')  # Mock configparser
    def test_get_guardian_articles_missing_config(self, mock_config_parser):
        # Mock the config parser to raise NoOptionError for missing API key
        mock_config = MagicMock()
        mock_config.get.side_effect = configparser.NoOptionError(
            'Missing key', 'api_key')
        mock_config_parser.return_value = mock_config

        # Check that ValueError is raised for missing configuration
        with self.assertRaises(ValueError):
            get_guardian_articles('test', 'test-stream')

    @patch('guardianapi.boto3.client')  # Mock the boto3 client
    @patch('guardianapi.requests.get')  # Mock the requests.get call
    @patch('guardianapi.configparser.ConfigParser')  # Mock configparser
    def test_get_guardian_articles_api_failure(
            self, mock_config_parser, mock_requests_get, mock_boto_client):
        # Mock the configuration parser to provide necessary parameters
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda section, key, fallback=None: {
            ('guardian', 'api_url'): 'https://content.guardianapis.com/search',
            ('guardian', 'api_key'): 'dummy_api_key',
            ('aws', 'access_key'): 'dummy_access_key',
            ('aws', 'secret_key'): 'dummy_secret_key',
            ('aws', 'region'): 'us-east-1',
            ('aws', 'retention_period'): '72'
        }[(section, key)]
        mock_config_parser.return_value = mock_config

        # Mock the response from the Guardian API to simulate an API failure
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_requests_get.return_value = mock_response

        # Check that an exception is raised for the API failure
        with self.assertRaises(Exception):
            get_guardian_articles(
                'test', 'test-stream', date_from='2024-01-01')


if __name__ == '__main__':
    unittest.main()
