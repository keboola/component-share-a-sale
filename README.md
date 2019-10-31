# Keboola ShareASale Extractor
ShareASale is an affiliate marketing network that services customer sets in affiliate marketing. It aids affiliates to find products to promote and earn commission for referrals on those products, while it aids merchants to implement, track and manage their affiliate program. 
The purpose of this extractor is to extractor all the related affiliates/merchants activity details and summary and their related products.

## API Documentation

API documentations can be found in ShareASale console under: 
    REPORT > API REPORTING 

## API limitations
Requests are limited to 600 per month. Available request credits will reset each month. ShareASale state that they cannot acommodate requests for additioanl credits.

Users are required to gauage their own API usage. It is also mandatory for users to set their IP Restriction of the account to "Require IP address match only for version 1.3 and lower".


## Parameters
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
5. Keyword
    - This is only needed when [Get Product] is selected as one of the endpoints.
    - Extractor can only accept one keyword per extractor configuration.
    - Input can either entered as a word or a phrase
6. Backfill Mode
    - Start date and end date parameter is needed when backfill mode is enabled
    - In normal extraction, extractor will automatically define request date range to last 2 days
    - Endpoints affected by Backfill Mode:

        1. Activity Details
        2. Merhant Timespan Report
        3. Traffic
    - Endpoints not affected by backfill mode means that the API returns from these endpoints are not bounded by date range. The API is either outputting the summary of the related matter or the current value/description of the subject.

