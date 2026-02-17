# Intial Authorization
# Implement refresh token flow
# Check if token is valid before making API calls, and refresh if needed
# Read the email list 
# For every email, create a new contact [RETRYING NEEDED]
#  Maske sure the cnotact is created
# For the new contact, add a tag
# Mautic recognizes this tag as part of a warming up campaign.
# Triggers an email send
# ACK that email is received.
# ACK that actions are performed bu bulldog
# Remove the tag, load next email address.

'''
# Error cases:
Access token not generated
    Do not retry cases
    1. Invalid URL - 404 Not found
    2. Unauthorized - 401

    Retry a fixed number of times
    1. Internal Server Error 500

    Retry with exponential backoff
    1. Rate limited - 429 - respect Rate Limited header
    2. Connection Timeout

Check if the current time is well within the validity of the access_token if not request a new token.
Persist this token
'''
'''
Get Contact 

HTTP Request

GET /contacts/ID

Response

Expected Response Code: 200
'''


'''
Create Contact

Create a new Contact.

HTTP Request

POST /contacts/new

POST Parameters

Name

Description

*

You can post any Contact field alias as a parameter. For example, firstname, lastname, email, etc.

ipAddress

IP address to associate with the Contact

lastActive

Date/time in UTC; preferably in the format of Y-m-d H:m:i but if that format fails, the string get sent through PHP’s strtotime then formatted

owner

ID of a Mautic User to assign this Contact to

overwriteWithBlank

If true, then empty values get set to fields. Otherwise empty values get skipped

Response

Expected Response Code: 201


        "owner": null,
        "ipAddresses": [],
        "tags": [
            {
                "id": 18,
                "tag": "glock-rocky",
                "description": null
            }
        ],
'''
# That should trigger an email send

# Today's task: 
# On stage create a new campaign and import some new contacts into it with a specific tag and see if they receive the email