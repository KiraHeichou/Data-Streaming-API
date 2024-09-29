The Data streaming project has the following files:
- guardianapi.py - this is the file with function that implements data streaming
- unittest_guardianapi.py - this is the file that has unit tests
- config.ini - this file needs to be configured with parameters (api keys, stream id etc.) before using the function. The parameters are self explanatory
- bandit_report.txt - the security vulnerability scan report done using bandit.

Usage:

To use the library, copy the guardianapi.py and config.ini to the project folder, import guardianapi into your project and run get_guardian_articles(...)

The following packages are to be installed to use the library:
 - requests
 - boto3
 - json
 - configparser
 - sys (this is used to run main function directly with parameters for demo)

To run the function directly from commandline, run guardianapi.py "search term" "optional date from"