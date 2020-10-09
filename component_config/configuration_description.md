# API limitations
Requests are limited to 600 per month. Available request credits will reset each month. ShareASale state that they cannot acommodate requests for additioanl credits.

Users are required to gauage their own API usage. It is also mandatory for users to set their IP Restriction of the account to "Require IP address match only for version 1.3 and lower".


# Parameters
1. Affiliate ID
    - Please acquire this from  ShareASale console

        REPORTS > API REPORTING
2. Token
    - Please acquire this from  ShareASale console
    
        REPORTS > API REPORTING
3. Secret Key
    - Please acquire this from  ShareASale console
    
        REPORTS > API REPORTING
4. Endpoint

    1. Activity Details
        - Detailed merchant activities
    2. Activity Summary
        - Activity summary to date
    3. Merchant Timespan Report
        - Extractor will break the requested date range into daily interval
        - Example

            - If requested date range is from 2019-01-01 to 2019-01-31, extractor will then request the endpoint with the days available within that range, meaning that there will be 31 requests just from this backfill request.
    4. Traffic
        - Web traffic report
    5. Get Products
        - A keyword or phrase is required to be entered in the configuration field below
    6. Traffic - Merchant grouped by Afftrack
        - Web traffic report group by afftrack for the list of merchants user input
        - **Note: At least one input table is required. The table needs to contain a column name , 'merchantID'. The extractor will use the values from this column to loop through all the merchants.
5. Keyword
    - This is only needed when [Get Product] is selected as one of the endpoints.
    - Extractor can only accept one keyword per extractor configuration.
    - Input can either entered as a word or a phrase
6. Incremental Period
    - Default: 1 day ago
    - Users are allowed to define their own incremental period they want; However, please leave this at default settings if adjustments are not necessary
    - Accepted parameters: # days ago, # months ago, # years ago
7. Backfill Mode
    - Start date and end date parameter is needed when backfill mode is enabled
    - In normal extraction, extractor will automatically define request date range to yesterday
    - Endpoints affected by Backfill Mode:

        1. Activity Details
        2. Merhant Timespan Report
        3. Traffic
        4. Traffic - Merchant grouped by Afftrack
    - Endpoints not affected by backfill mode means that the API returns from these endpoints are not bounded by date range. The API is either outputting the summary of the related matter or the current value/description of the subject.